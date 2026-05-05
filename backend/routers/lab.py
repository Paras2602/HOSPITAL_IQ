from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import json, os, shutil, re
from datetime import datetime
from backend.database import get_db
from backend.models.user import User, UserRole, LabProfile
from backend.models.lab import LabRequest, LabReport, LabRequestStatus
from backend.models.patient import PatientProfile
from backend.utils.deps import get_current_user, require_role

router = APIRouter(prefix="/lab", tags=["lab"])
lab_required = require_role(UserRole.lab, UserRole.admin)

UPLOAD_DIR = "uploads/lab"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── OCR / PDF Text Extraction Helpers ──────────────────────────────

LAB_VALUE_PATTERNS = {
    "HbA1c": r"(?:HbA1c|Glycated\s*Hemoglobin)[:\s]*([0-9]+\.?[0-9]*)\s*%?",
    "Glucose": r"(?:Glucose|Blood\s*Sugar|FBS|Fasting\s*Blood\s*Sugar)[:\s]*([0-9]+\.?[0-9]*)",
    "Creatinine": r"(?:Creatinine|Serum\s*Creatinine)[:\s]*([0-9]+\.?[0-9]*)",
    "Cholesterol": r"(?:Total\s*Cholesterol|Cholesterol)[:\s]*([0-9]+\.?[0-9]*)",
    "Hemoglobin": r"(?:Hemoglobin|Hb|Haemoglobin)[:\s]*([0-9]+\.?[0-9]*)",
    "WBC": r"(?:WBC|White\s*Blood\s*Cell|Leucocyte)[:\s]*([0-9]+\.?[0-9]*)",
    "RBC": r"(?:RBC|Red\s*Blood\s*Cell|Erythrocyte)[:\s]*([0-9]+\.?[0-9]*)",
    "Platelets": r"(?:Platelet|PLT)[:\s]*([0-9]+\.?[0-9]*)",
    "Bilirubin": r"(?:Total\s*Bilirubin|Bilirubin)[:\s]*([0-9]+\.?[0-9]*)",
    "ALT": r"(?:ALT|SGPT|Alanine\s*Aminotransferase)[:\s]*([0-9]+\.?[0-9]*)",
    "AST": r"(?:AST|SGOT|Aspartate\s*Aminotransferase)[:\s]*([0-9]+\.?[0-9]*)",
    "Albumin": r"(?:Albumin)[:\s]*([0-9]+\.?[0-9]*)",
    "Urea": r"(?:Blood\s*Urea|BUN|Urea)[:\s]*([0-9]+\.?[0-9]*)",
    "Sodium": r"(?:Sodium|Na)[:\s]*([0-9]+\.?[0-9]*)",
    "Potassium": r"(?:Potassium|K)[:\s]*([0-9]+\.?[0-9]*)",
    "Alkaline_Phosphatase": r"(?:Alkaline\s*Phosph[oa]tase|ALP)[:\s]*([0-9]+\.?[0-9]*)",
}


def parse_lab_text(text: str) -> dict:
    """Extract common lab values from raw text using regex patterns."""
    extracted = {}
    for name, pattern in LAB_VALUE_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted[name] = match.group(1)
    return extracted


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text
    except Exception:
        return ""


def extract_text_from_image(filepath: str) -> str:
    """Extract text from an image using pytesseract OCR."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(filepath)
        text = pytesseract.image_to_string(img)
        return text
    except Exception:
        return ""


@router.get("/profile")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(LabProfile).where(LabProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Lab profile not found")
    return {
        "id": profile.id,
        "department_name": profile.department_name,
        "services": profile.services,
        "contact": profile.contact,
        "timing": profile.timing,
        "email": current_user.email,
    }


@router.get("/requests")
async def get_lab_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(lab_required),
):
    result = await db.execute(
        select(LabRequest).order_by(LabRequest.created_at.desc())
    )
    requests = result.scalars().all()
    out = []
    for r in requests:
        pp = (await db.execute(select(PatientProfile).where(PatientProfile.id == r.patient_id))).scalar_one_or_none()
        out.append({
            "id": r.id,
            "patient_name": pp.full_name if pp else "Unknown",
            "patient_id": pp.patient_id if pp else "",
            "tests_requested": json.loads(r.tests_requested or "[]"),
            "priority": r.priority,
            "status": r.status.value,
            "notes": r.notes,
            "created_at": r.created_at.isoformat(),
        })
    return out


@router.post("/upload/{lab_request_id}")
async def upload_lab_result(
    lab_request_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(lab_required),
):
    lp_result = await db.execute(
        select(LabProfile).where(LabProfile.user_id == current_user.id)
    )
    lp = lp_result.scalar_one_or_none()

    lr_result = await db.execute(select(LabRequest).where(LabRequest.id == lab_request_id))
    lab_req = lr_result.scalar_one_or_none()
    if not lab_req:
        raise HTTPException(status_code=404, detail="Lab request not found")

    # Save file
    filename = f"{lab_request_id}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse based on file type
    extracted = {}
    lower_filename = file.filename.lower()
    
    if lower_filename.endswith(".csv"):
        import pandas as pd
        df = pd.read_csv(filepath)
        extracted = df.iloc[0].to_dict() if len(df) > 0 else {}
    elif lower_filename.endswith(".xlsx"):
        import pandas as pd
        df = pd.read_excel(filepath)
        extracted = df.iloc[0].to_dict() if len(df) > 0 else {}
    elif lower_filename.endswith(".pdf"):
        text = extract_text_from_pdf(filepath)
        extracted = parse_lab_text(text)
    elif lower_filename.endswith((".png", ".jpg", ".jpeg")):
        text = extract_text_from_image(filepath)
        extracted = parse_lab_text(text)

    # Clean extracted values (remove None/NaN)
    extracted = {k: str(v) for k, v in extracted.items() if v is not None and str(v).lower() != "nan"}

    report = LabReport(
        lab_request_id=lab_request_id,
        lab_id=lp.id if lp else "",
        patient_id=lab_req.patient_id,
        file_url=filepath,
        extracted_values=json.dumps({k: str(v) for k, v in extracted.items()}),
        validated_values=json.dumps({k: str(v) for k, v in extracted.items()}),
    )
    db.add(report)
    lab_req.status = LabRequestStatus.completed
    await db.commit()

    return {
        "message": "Report uploaded",
        "report_id": report.id,
        "extracted_values": extracted,
    }


@router.post("/upload/manual")
async def upload_manual_values(
    patient_profile_id: str,
    values: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(lab_required),
):
    lp_result = await db.execute(
        select(LabProfile).where(LabProfile.user_id == current_user.id)
    )
    lp = lp_result.scalar_one_or_none()
    report = LabReport(
        lab_id=lp.id if lp else "",
        patient_id=patient_profile_id,
        extracted_values=json.dumps(values),
        validated_values=json.dumps(values),
    )
    db.add(report)
    await db.commit()
    return {"message": "Values saved", "report_id": report.id}


@router.patch("/reports/{report_id}/publish")
async def publish_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(lab_required),
):
    result = await db.execute(select(LabReport).where(LabReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.is_published = True
    report.published_at = datetime.utcnow()
    await db.commit()
    return {"message": "Report published"}


@router.get("/reports/all")
async def get_all_reports(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(lab_required),
):
    result = await db.execute(select(LabReport).order_by(LabReport.created_at.desc()).limit(50))
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "is_published": r.is_published,
            "extracted_values": json.loads(r.extracted_values or "{}"),
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]

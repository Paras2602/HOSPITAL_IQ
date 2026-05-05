from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import os
import uuid
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import json
from backend.database import get_db
from backend.models.user import User, UserRole, DoctorProfile
from backend.models.patient import PatientProfile
from backend.models.appointment import Appointment, AppointmentStatus
from backend.models.prediction import PredictionRecord, HealthScore
from backend.models.lab import LabReport
from backend.utils.deps import get_current_user, require_role

router = APIRouter(prefix="/patient", tags=["patient"])
patient_required = require_role(UserRole.patient, UserRole.doctor, UserRole.admin)


@router.get("/profile")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    pp = result.scalar_one_or_none()
    if not pp:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    return {
        "id": pp.id,
        "patient_id": pp.patient_id,
        "full_name": pp.full_name,
        "age": pp.age,
        "sex": pp.sex,
        "blood_group": pp.blood_group,
        "height_cm": pp.height_cm,
        "weight_kg": pp.weight_kg,
        "address": pp.address,
        "father_name": pp.father_name,
        "mother_name": pp.mother_name,
        "emergency_contact": pp.emergency_contact,
        "allergies": pp.allergies,
        "chronic_conditions": pp.chronic_conditions,
        "photo_url": pp.photo_url,
        "profile_complete": pp.profile_complete,
        "email": current_user.email,
        "phone": current_user.phone,
    }


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    blood_group: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    address: Optional[str] = None
    father_name: Optional[str] = None
    father_contact: Optional[str] = None
    mother_name: Optional[str] = None
    mother_contact: Optional[str] = None
    emergency_contact: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    photo_url: Optional[str] = None


@router.put("/profile")
async def update_profile(
    req: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    pp = result.scalar_one_or_none()
    if not pp:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    # Update fields
    update_data = req.model_dump(exclude_none=True)
    for field, val in update_data.items():
        setattr(pp, field, val)

    # Mark complete if key fields filled (allow zero for numeric fields just in case)
    if (pp.full_name and 
        (pp.age is not None) and 
        pp.sex and 
        (pp.height_cm is not None) and 
        (pp.weight_kg is not None)):
        pp.profile_complete = True
    else:
        pp.profile_complete = False

    try:
        await db.commit()
        await db.refresh(pp)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"message": "Profile updated", "patient_id": pp.patient_id, "complete": pp.profile_complete}


@router.post("/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    pp = result.scalar_one_or_none()
    if not pp:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"patient_{pp.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join("uploads", filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"http://localhost:8000/uploads/{filename}"
    pp.photo_url = url

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"message": "Photo uploaded", "photo_url": url}


@router.get("/doctors")
async def list_doctors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DoctorProfile))
    doctors = result.scalars().all()
    return [
        {
            "id": d.id,
            "user_id": d.user_id,
            "full_name": d.full_name,
            "specialization": d.specialization,
            "qualification": d.qualification,
            "years_experience": d.years_experience,
            "success_rate": d.success_rate,
            "available_slots": json.loads(d.available_slots or "[]"),
        }
        for d in doctors
    ]


from backend.models.symptom_models import DiagnosisSession


class BookAppointmentRequest(BaseModel):
    doctor_profile_id: str
    requested_date: str
    requested_slot: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis_session_id: Optional[str] = None


@router.post("/appointments")
async def book_appointment(
    req: BookAppointmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pp_result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    pp = pp_result.scalar_one_or_none()
    if not pp:
        raise HTTPException(status_code=404, detail="Complete your profile first")

    appt = Appointment(
        patient_id=pp.id,
        doctor_id=req.doctor_profile_id,
        requested_date=req.requested_date,
        requested_slot=req.requested_slot,
        symptoms=req.symptoms,
        status=AppointmentStatus.pending,
    )
    db.add(appt)
    await db.flush() # To get the appt.id

    # If diagnosis_session_id is provided, link it
    if req.diagnosis_session_id:
        sess_result = await db.execute(
            select(DiagnosisSession).where(DiagnosisSession.session_id == req.diagnosis_session_id)
        )
        sess = sess_result.scalar_one_or_none()
        if sess:
            sess.follow_up_appointment_id = appt.id

    await db.commit()
    return {"message": "Appointment booked", "appointment_id": appt.id}


@router.get("/appointments")
async def get_my_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pp_result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    pp = pp_result.scalar_one_or_none()
    if not pp:
        return []

    result = await db.execute(
        select(Appointment).where(Appointment.patient_id == pp.id)
        .order_by(Appointment.created_at.desc())
    )
    appts = result.scalars().all()
    out = []
    for a in appts:
        dr = (await db.execute(select(DoctorProfile).where(DoctorProfile.id == a.doctor_id))).scalar_one_or_none()
        out.append({
            "id": a.id,
            "doctor_name": dr.full_name if dr else "Unknown",
            "doctor_specialization": dr.specialization if dr else "",
            "requested_date": a.requested_date,
            "requested_slot": a.requested_slot,
            "confirmed_slot": a.confirmed_slot,
            "status": a.status.value,
        })
    return out


@router.get("/predictions")
async def get_my_predictions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pp_result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    pp = pp_result.scalar_one_or_none()
    if not pp:
        return []

    result = await db.execute(
        select(PredictionRecord).where(PredictionRecord.patient_id == pp.id)
        .order_by(PredictionRecord.created_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "disease": r.disease,
            "risk_probability": r.risk_probability,
            "risk_label": r.risk_label,
            "shap_values": json.loads(r.shap_values or "{}"),
            "recommendations": r.recommendations,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/health-score")
async def get_health_score(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pp_result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    pp = pp_result.scalar_one_or_none()
    if not pp:
        return []

    result = await db.execute(
        select(HealthScore).where(HealthScore.patient_id == pp.id)
        .order_by(HealthScore.recorded_at.asc())
    )
    scores = result.scalars().all()
    return [
        {
            "score": s.score,
            "diabetes_risk": s.diabetes_risk,
            "heart_risk": s.heart_risk,
            "ckd_risk": s.ckd_risk,
            "liver_risk": s.liver_risk,
            "recorded_at": s.recorded_at.isoformat(),
        }
        for s in scores
    ]


@router.get("/lab-reports")
async def get_lab_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pp_result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    pp = pp_result.scalar_one_or_none()
    if not pp:
        return []

    result = await db.execute(
        select(LabReport).where(
            LabReport.patient_id == pp.id,
            LabReport.is_published == True,
        ).order_by(LabReport.created_at.desc())
    )
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "extracted_values": json.loads(r.extracted_values or "{}"),
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr
from typing import Optional
from backend.database import get_db
from backend.models.user import User, UserRole, DoctorProfile, LabProfile
from backend.models.patient import PatientProfile
from backend.models.prediction import AuditLog, PredictionRecord
from backend.utils.security import hash_password, generate_access_code
from backend.utils.deps import require_role

router = APIRouter(prefix="/admin", tags=["admin"])
admin_required = require_role(UserRole.admin)


class CreateDoctorRequest(BaseModel):
    full_name: str
    specialization: str
    qualification: str
    years_experience: Optional[int] = None
    success_rate: Optional[float] = None
    photo_url: Optional[str] = None
    available_slots: Optional[str] = None # JSON string list


class CreateLabRequest(BaseModel):
    department_name: str
    services: Optional[str] = None
    contact: Optional[str] = None
    timing: Optional[str] = None


@router.post("/doctors")
async def create_doctor(
    req: CreateDoctorRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_required),
):
    code = generate_access_code()
    # Generate a secure random password for the user account
    import secrets, string
    secure_password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for i in range(12)) # Example: 12 chars, letters, digits, punctuation
    hashed_password = hash_password(secure_password)

    user = User(
        email=f"pending_{code}@hospitaliq.local", # Keep placeholder email for initial state
        hashed_password=hashed_password,
        role=UserRole.doctor,
        access_code=code, # Store the access code for activation
    )
    db.add(user)
    await db.flush() # Flush to get user.id before creating profile
    profile = DoctorProfile(
        user_id=user.id,
        full_name=req.full_name,
        specialization=req.specialization,
        qualification=req.qualification,
        years_experience=req.years_experience,
        success_rate=req.success_rate,
        photo_url=req.photo_url,
        available_slots=req.available_slots,
    )
    db.add(profile)
    await db.commit()
    return {"user_id": user.id, "access_code": code, "secure_password": secure_password, "message": "Doctor account created. Share access code and initial password with the user for activation."}


@router.post("/upload-photo")
async def upload_admin_photo(
    file: UploadFile = File(...),
    _: User = Depends(admin_required),
):
    import uuid, os, shutil
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    # Sanitize filename to prevent path traversal issues
    safe_filename = re.sub(r'[^\w\-_\. ]', '_', file.filename)
    filename = f"admin_photo_{uuid.uuid4().hex[:8]}.{ext}" # Use UUID for uniqueness
    filepath = os.path.join("uploads", filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Use a configurable base URL for uploads
    base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
    return {"photo_url": f"{base_url}/uploads/{filename}"}


@router.post("/labs")
async def create_lab(
    req: CreateLabRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_required),
):
    code = generate_access_code()
    # Generate a secure random password for the user account
    import secrets, string
    secure_password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for i in range(12)) # Example: 12 chars, letters, digits, punctuation
    hashed_password = hash_password(secure_password)

    user = User(
        email=f"pending_{code}@hospitaliq.local", # Keep placeholder email for initial state
        hashed_password=hashed_password,
        role=UserRole.lab,
        access_code=code, # Store the access code for activation
    )
    db.add(user)
    await db.flush() # Flush to get user.id before creating profile
    profile = LabProfile(
        user_id=user.id,
        department_name=req.department_name,
        services=req.services,
        contact=req.contact,
        timing=req.timing,
    )
    db.add(profile)
    await db.commit()
    return {"user_id": user.id, "access_code": code, "secure_password": secure_password, "message": "Lab account created. Share access code and initial password with the user for activation."}


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required), # Use current_user for potential future checks
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active,
            "access_code": u.access_code if u.access_code else "N/A", # Indicate if code is used/null
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.get("/users/{user_id}/patient-profile")
async def get_patient_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    # Ensure the user_id corresponds to a patient role before fetching profile
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or user.role != UserRole.patient:
        raise HTTPException(status_code=404, detail="Patient user not found or not a patient role")

    result = await db.execute(select(PatientProfile).where(PatientProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return profile


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    total_patients = (
        await db.execute(select(func.count(PatientProfile.id)))
    ).scalar()
    total_doctors = (
        await db.execute(select(func.count(DoctorProfile.id)))
    ).scalar()
    total_predictions = (
        await db.execute(select(func.count(PredictionRecord.id)))
    ).scalar()

    # Clinical Safety Metrics
    from backend.models.symptom_models import DiagnosisSession, DiagnosisAuditLog
    low_confidence_count = (
        await db.execute(
            select(func.count(DiagnosisSession.id))
            .where(DiagnosisSession.status.in_(["low_confidence", "inconclusive"]))
        )
    ).scalar()
    
    high_risk_alerts = (
        await db.execute(
            select(func.count(DiagnosisAuditLog.id))
            .where(DiagnosisAuditLog.action == "high_risk_alert_triggered")
        )
    ).scalar()

    # disease breakdown
    disease_result = await db.execute(
        select(PredictionRecord.disease, func.count(PredictionRecord.id))
        .group_by(PredictionRecord.disease)
    )
    disease_counts = {row[0]: row[1] for row in disease_result}

    return {
        "total_users": total_users,
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_predictions": total_predictions,
        "disease_counts": disease_counts,
        "low_confidence_count": low_confidence_count,
        "high_risk_alerts": high_risk_alerts
    }


@router.get("/audit-logs")
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "action": l.action,
            "resource": l.resource,
            "details": l.details,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.patch("/users/{user_id}/toggle")
async def toggle_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deactivating the last admin user if that's a requirement
    if user.role == UserRole.admin and not current_user.id == user_id: # Cannot deactivate self if last admin
        admins = await db.execute(select(User.id).where(User.role == UserRole.admin, User.is_active == True))
        if len(admins.scalars().all()) <= 1:
            raise HTTPException(status_code=400, detail="Cannot deactivate the last admin user")

    from backend.utils.logging import log_action
    user.is_active = not user.is_active
    await log_action(db, current_user.id, "toggle_user", f"user:{user_id}", f"Set is_active to {user.is_active}")
    await db.commit()
    return {"user_id": user_id, "is_active": user.is_active}

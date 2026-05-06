from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime
from backend.database import get_db
from backend.models.user import User, UserRole, DoctorProfile
from backend.models.patient import PatientProfile
from backend.models.appointment import Appointment, AppointmentStatus, ClinicalNote
from backend.models.lab import LabRequest, LabReport
from backend.models.prediction import PredictionRecord, HealthScore
from backend.utils.deps import get_current_user, require_role

router = APIRouter(prefix="/doctor", tags=["doctor"])
doctor_required = require_role(UserRole.doctor, UserRole.admin)


@router.get("/profile")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return {
        "id": profile.id,
        "full_name": profile.full_name,
        "specialization": profile.specialization,
        "qualification": profile.qualification,
        "years_experience": profile.years_experience,
        "success_rate": profile.success_rate,
        "available_slots": json.loads(profile.available_slots or "[]"),
        "email": current_user.email,
    }


class UpdateSlotsRequest(BaseModel):
    slots: list[str]


@router.put("/slots")
async def update_slots(
    req: UpdateSlotsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    profile.available_slots = json.dumps(req.slots)
    await db.commit()
    return {"message": "Slots updated"}


@router.get("/appointments")
async def get_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dp_result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
    )
    dp = dp_result.scalar_one_or_none()
    if not dp:
        return []

    result = await db.execute(
        select(Appointment).where(Appointment.doctor_id == dp.id)
        .order_by(Appointment.created_at.desc())
    )
    appts = result.scalars().all()
    
    from backend.models.symptom_models import DiagnosisSession
    
    out = []
    for a in appts:
        pp = (await db.execute(select(PatientProfile).where(PatientProfile.id == a.patient_id))).scalar_one_or_none()
        
        # Check for linked diagnosis session
        sess_result = await db.execute(select(DiagnosisSession).where(DiagnosisSession.follow_up_appointment_id == a.id))
        sess = sess_result.scalar_one_or_none()
        
        out.append({
            "id": a.id,
            "patient_name": pp.full_name if pp else "Unknown",
            "patient_id": pp.patient_id if pp else "",
            "requested_date": a.requested_date,
            "requested_slot": a.requested_slot,
            "confirmed_slot": a.confirmed_slot,
            "status": a.status.value,
            "symptoms": a.symptoms,
            "notes": a.notes,
            "diagnosis_session_id": sess.session_id if sess else None
        })
    return out


class ConfirmApptRequest(BaseModel):
    confirmed_slot: str


@router.patch("/appointments/{appt_id}/confirm")
async def confirm_appointment(
    appt_id: str,
    req: ConfirmApptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(doctor_required),
):
    result = await db.execute(select(Appointment).where(Appointment.id == appt_id))
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appt.status = AppointmentStatus.confirmed
    appt.confirmed_slot = req.confirmed_slot
    
    # Send Notifications
    try:
        from backend.utils.notifications import email_service
        
        # Get patient and doctor details
        patient_res = await db.execute(select(PatientProfile, User.email).join(User, PatientProfile.user_id == User.id).where(PatientProfile.id == appt.patient_id))
        patient_data = patient_res.first()
        
        if patient_data:
            pp, p_email = patient_data
            # Email to Patient
            email_service.send_appointment_confirmation(
                to_email=p_email,
                patient_name=pp.full_name,
                doctor_name=current_user.name,
                date=appt.requested_date,
                time=req.confirmed_slot
            )
            # Email to Doctor
            email_service.send_email(
                to_email=current_user.email,
                subject=f"Appointment Confirmed: {pp.full_name}",
                body=f"You have a confirmed appointment with {pp.full_name} on {appt.requested_date} at {req.confirmed_slot}."
            )
    except Exception as e:
        print(f"Notification error: {e}")

    await db.commit()
    return {"message": "Appointment confirmed"}


@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(doctor_required),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.patient_id == patient_id)
    )
    pp = result.scalar_one_or_none()
    if not pp:
        raise HTTPException(status_code=404, detail="Patient not found")

    hs_result = await db.execute(
        select(HealthScore).where(HealthScore.patient_id == pp.id)
        .order_by(HealthScore.recorded_at.desc())
        .limit(1)
    )
    latest_hs = hs_result.scalars().first()

    return {
        "id": pp.id,
        "patient_id": pp.patient_id,
        "full_name": pp.full_name,
        "age": pp.age,
        "sex": pp.sex,
        "blood_group": pp.blood_group,
        "health_score": latest_hs.score if latest_hs else 100.0,
        "height_cm": pp.height_cm,
        "weight_kg": pp.weight_kg,
        "address": pp.address,
        "father_name": pp.father_name,
        "father_contact": pp.father_contact,
        "mother_name": pp.mother_name,
        "mother_contact": pp.mother_contact,
        "emergency_contact": pp.emergency_contact,
        "allergies": pp.allergies,
        "chronic_conditions": pp.chronic_conditions,
        "profile_complete": pp.profile_complete,
    }


class ClinicalNoteRequest(BaseModel):
    appointment_id: Optional[str] = None
    patient_profile_id: str
    diagnosis: Optional[str] = None
    symptoms: Optional[str] = None
    vitals: Optional[dict] = None
    history_update: Optional[str] = None
    recommended_tests: Optional[str] = None


@router.post("/clinical-notes")
async def add_clinical_note(
    req: ClinicalNoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(doctor_required),
):
    dp_result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
    )
    dp = dp_result.scalar_one_or_none()
    note = ClinicalNote(
        appointment_id=req.appointment_id,
        patient_profile_id=req.patient_profile_id,
        doctor_profile_id=dp.id if dp else "",
        diagnosis=req.diagnosis,
        symptoms=req.symptoms,
        vitals=json.dumps(req.vitals) if req.vitals else None,
        history_update=req.history_update,
        recommended_tests=req.recommended_tests,
    )
    db.add(note)
    await db.commit()
    return {"message": "Clinical note saved", "note_id": note.id}


class LabRequestCreate(BaseModel):
    patient_profile_id: str
    tests_requested: list[str]
    priority: str = "normal"
    notes: Optional[str] = None


@router.post("/lab-requests")
async def create_lab_request(
    req: LabRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(doctor_required),
):
    dp_result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
    )
    dp = dp_result.scalar_one_or_none()
    lr = LabRequest(
        patient_id=req.patient_profile_id,
        doctor_id=dp.id if dp else "",
        tests_requested=json.dumps(req.tests_requested),
        priority=req.priority,
        notes=req.notes,
    )
    db.add(lr)
    await db.commit()
    return {"message": "Lab request created", "request_id": lr.id}


@router.get("/lab-results/{patient_profile_id}")
async def get_lab_results(
    patient_profile_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(doctor_required),
):
    result = await db.execute(
        select(LabReport).where(LabReport.patient_id == patient_profile_id)
        .where(LabReport.is_published == True)
    )
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "extracted_values": json.loads(r.extracted_values or "{}"),
            "validated_values": json.loads(r.validated_values or "{}"),
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]


@router.get("/prediction-history/{patient_profile_id}")
async def get_prediction_history(
    patient_profile_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(doctor_required),
):
    result = await db.execute(
        select(PredictionRecord)
        .where(PredictionRecord.patient_id == patient_profile_id)
        .order_by(PredictionRecord.created_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "disease": r.disease,
            "risk_probability": r.risk_probability,
            "risk_label": r.risk_label,
            "recommendations": r.recommendations,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/clinical-notes")
async def get_clinical_notes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(doctor_required),
):
    dp_result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
    )
    dp = dp_result.scalar_one_or_none()
    if not dp:
        return []

    result = await db.execute(
        select(ClinicalNote).where(ClinicalNote.doctor_profile_id == dp.id)
        .order_by(ClinicalNote.created_at.desc())
    )
    notes = result.scalars().all()
    out = []
    for n in notes:
        pp = (await db.execute(select(PatientProfile).where(PatientProfile.id == n.patient_profile_id))).scalar_one_or_none()
        out.append({
            "id": n.id,
            "patient_name": pp.full_name if pp else "Unknown",
            "diagnosis": n.diagnosis,
            "symptoms": n.symptoms,
            "vitals": json.loads(n.vitals) if n.vitals else {},
            "recommended_tests": n.recommended_tests,
            "created_at": n.created_at.isoformat(),
        })
    return out


@router.get("/lab-requests")
async def get_my_lab_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(doctor_required),
):
    dp_result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
    )
    dp = dp_result.scalar_one_or_none()
    if not dp:
        return []

    result = await db.execute(
        select(LabRequest).where(LabRequest.doctor_id == dp.id)
        .order_by(LabRequest.created_at.desc())
    )
    reqs = result.scalars().all()
    out = []
    for r in reqs:
        pp = (await db.execute(select(PatientProfile).where(PatientProfile.id == r.patient_id))).scalar_one_or_none()
        out.append({
            "id": r.id,
            "patient_name": pp.full_name if pp else "Unknown",
            "tests": json.loads(r.tests_requested or "[]"),
            "priority": r.priority,
            "status": r.status.value,
            "created_at": r.created_at.isoformat(),
        })
    return out

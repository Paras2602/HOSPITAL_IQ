import uuid
import os
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from backend.database import get_db
from backend.models.user import User, UserRole, DoctorProfile
from backend.models.patient import PatientProfile
from backend.models.symptom_models import (
    Symptom, Disease, Medicine, DiagnosisSession,
    DiagnosisAuditLog, Prescription, DiseaseMedicineMapping
)
from backend.utils.deps import get_current_user as authenticated, require_role
from backend.ml.symptom_disease_predictor import SymptomDiseasePredictor
from backend.ml.prescription_generator import PrescriptionGenerator
from backend.utils.notifications import tts_service, translation_service
from backend.utils.pdf_generator import generate_prescription_pdf
from backend.utils.logging import log_action

# Initialize predictor
predictor = SymptomDiseasePredictor()

rx_generator = PrescriptionGenerator()
router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])
admin_required = require_role(UserRole.admin)
doctor_required = require_role(UserRole.doctor)

# Request Schemas
class DiagnosisRequest(BaseModel):
    symptoms: List[str]
    initiated_by: str = "patient"
    patient_id: Optional[str] = None

class ShareRequest(BaseModel):
    diagnosis_session_id: str
    doctor_id: str

class VoiceSummaryRequest(BaseModel):
    session_id: str
    language: str = "en"

class TranslateRequest(BaseModel):
    session_id: str
    target_language: str

@router.get("/symptoms")
async def get_symptoms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Symptom).where(Symptom.is_active == True))
    symptoms = result.scalars().all()
    
    # Group by category
    categories_map = {}
    for s in symptoms:
        if s.category not in categories_map:
            categories_map[s.category] = []
        categories_map[s.category].append({
            "id": s.id,
            "name": s.name,
            "display_name": s.display_name,
            "category": s.category,
            "severity_weight": s.severity_weight
        })
    
    return {
        "categories": [
            {"name": cat, "symptoms": symps}
            for cat, symps in categories_map.items()
        ]
    }

@router.get("/medicines")
async def get_medicines(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Medicine).where(Medicine.is_active == True))
    meds = result.scalars().all()
    grouped: dict = {}
    for m in meds:
        t = m.medicine_type or "General"
        if t not in grouped:
            grouped[t] = []
        grouped[t].append({
            "id": m.id, "name": m.name, "generic_name": m.generic_name,
            "dosage": m.default_dosage, "frequency": m.frequency,
            "medicine_type": m.medicine_type,
            "common_side_effects": m.common_side_effects,
        })
    return grouped

@router.post("/predict")
async def predict_disease(
    req: DiagnosisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    if len(req.symptoms) < 3:
        raise HTTPException(status_code=400, detail="Minimum 3 symptoms required for analysis")
    
    try:
        # Run prediction
        prediction = predictor.predict(req.symptoms)
        
        # Get disease details (severity/description) for each prediction
        for pred in prediction["predictions"]:
            dis_res = await db.execute(select(Disease).where(Disease.name == pred["disease"]))
            dis = dis_res.scalar_one_or_none()
            if dis:
                pred["severity"] = dis.severity
                pred["description"] = dis.description
        
        # Save session
        session_id = f"DX-{uuid.uuid4().hex[:8].upper()}"
        new_session = DiagnosisSession(
            session_id=session_id,
            patient_id=req.patient_id or (current_user.id if current_user.role == UserRole.patient else None),
            initiated_by=req.initiated_by,
            symptoms_input=req.symptoms,
            predicted_diseases=prediction["predictions"],
            top_prediction=prediction["predictions"][0]["disease"] if prediction["predictions"] else "Unknown",
            top_confidence=prediction["predictions"][0]["confidence"] if prediction["predictions"] else 0.0,
            status="pending"
        )
        
        # Health Advice (hardcoded template for now)
        prediction["health_advice"] = f"Based on your symptoms ({', '.join(req.symptoms)}), our AI suggests a potential match for {new_session.top_prediction}. Please review the details below and consult with a doctor."
        prediction["session_id"] = session_id
        
        db.add(new_session)
        await db.commit()

        # Strip medicine info for patient-initiated predictions
        if req.initiated_by == "patient":
            for pred in prediction.get("predictions", []):
                pred.pop("recommended_medicines", None)
                pred.pop("medicines", None)

        return prediction
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/share-with-doctor")
async def share_with_doctor(
    req: ShareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    result = await db.execute(select(DiagnosisSession).where(DiagnosisSession.session_id == req.diagnosis_session_id))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    
    sess.doctor_id = req.doctor_id
    sess.status = "shared"
    
    # Audit log
    log = DiagnosisAuditLog(
        diagnosis_session_id=sess.id,
        action="shared_with_doctor",
        performed_by_role=current_user.role.value,
        performed_by_id=current_user.id,
        details=f"Shared with doctor {req.doctor_id}"
    )
    db.add(log)
    
    # Also log to main system audit log
    await log_action(db, current_user.id, "diagnosis_shared", f"session:{sess.session_id}", f"Shared with doctor {req.doctor_id}")
    
    await db.commit()
    return {"message": "Diagnosis shared with doctor"}

@router.post("/predict/voice-summary")
async def get_voice_summary(
    req: VoiceSummaryRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DiagnosisSession).where(DiagnosisSession.session_id == req.session_id))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    
    text = f"Diagnosis Summary. Your reported symptoms include {', '.join(sess.symptoms_input)}. The top predicted condition is {sess.top_prediction} with {sess.top_confidence:.1f}% confidence. This report has been shared for clinical review."
    
    tts_res = tts_service.text_to_speech(text, language=req.language)
    return {"audio_url": tts_res.get("url", "")}

@router.post("/predict/translate")
async def translate_prediction(
    req: TranslateRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DiagnosisSession).where(DiagnosisSession.session_id == req.session_id))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    
    text = f"Top Prediction: {sess.top_prediction}. Confidence: {sess.top_confidence:.1f}%. Symptoms: {', '.join(sess.symptoms_input)}."
    
    trans_res = translation_service.translate(text, target_language=req.target_language)
    return {"translated_text": trans_res.get("translated", "")}

@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    session = (await db.execute(select(DiagnosisSession).filter_by(session_id=session_id))).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Authorization check:
    # Patients can access their own sessions.
    # Doctors can access sessions they are assigned to (doctor_id matches current user).
    # Admins can access any session.
    is_admin = current_user.role == UserRole.admin
    is_patient_owner = current_user.id == session.patient_id
    is_assigned_doctor = current_user.role == UserRole.doctor and current_user.id == session.doctor_id

    if not is_admin and not is_patient_owner and not is_assigned_doctor:
        raise HTTPException(status_code=403, detail="Not authorized to access this diagnosis session")
    
    return session

@router.get("/history/{patient_id}")
async def get_history(
    patient_id: str,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    # Fetch the patient profile to verify existence and potentially check doctor-patient link if needed.
    pp_result = await db.execute(select(PatientProfile).where(PatientProfile.user_id == patient_id))
    pp_requested = pp_result.scalar_one_or_none()
    if not pp_requested:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    # Authorization check:
    # Patients can access their own history.
    # Doctors can access history for patients they are assigned to (requires additional checks, currently not implemented).
    # Admins can access any history.
    is_admin = current_user.role == UserRole.admin
    is_patient_owner = current_user.id == patient_id # Check if the current user is the owner of the profile

    # If not admin and not the patient owner, deny access.
    # Doctors' access to patient history needs specific assignment/relationship logic.
    if not is_admin and not is_patient_owner:
        raise HTTPException(status_code=403, detail="Not authorized to access this patient's diagnosis history")

    result = await db.execute(
        select(DiagnosisSession)
        .filter_by(patient_id=patient_id)
        .order_by(desc(DiagnosisSession.created_at))
        .offset(offset).limit(limit)
    )
    return result.scalars().all()

@router.get("/doctor/{doctor_id}")
async def get_doctor_sessions(
    doctor_id: str,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated) # Authenticated user
):
    # Authorization check:
    # Doctors can access their own sessions.
    # Admins can access any doctor's sessions.
    is_admin = current_user.role == UserRole.admin
    is_target_doctor = current_user.role == UserRole.doctor and current_user.id == doctor_id

    if not is_admin and not is_target_doctor:
        raise HTTPException(status_code=403, detail="Not authorized to access this doctor's sessions")

    result = await db.execute(
        select(DiagnosisSession)
        .filter_by(doctor_id=doctor_id) # Filter by the requested doctor_id
        .order_by(desc(DiagnosisSession.created_at))
        .offset(offset).limit(limit)
    )
    return result.scalars().all()

# ── Prescription Endpoints ─────────────────────────────────

class PrescriptionGenerateRequest(BaseModel):
    diagnosis_session_id: str
    patient_id: Optional[str] = None
    disease_confirmed: str
    medicines: List[dict]
    precautions: Optional[str] = ""
    dietary_advice: Optional[str] = ""
    follow_up_days: int = 15

@router.post("/prescription/generate")
async def generate_prescription(
    req: PrescriptionGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    if current_user.role != UserRole.doctor:
        raise HTTPException(403, "Only doctors can generate prescriptions")

    sess_res = await db.execute(select(DiagnosisSession).where(
        DiagnosisSession.session_id == req.diagnosis_session_id))
    sess = sess_res.scalar_one_or_none()
    if not sess:
        raise HTTPException(404, "Diagnosis session not found")

    # Get patient profile
    p_id = req.patient_id or sess.patient_id
    patient_data = {"name": "Unknown", "age": "N/A", "sex": "N/A",
                    "weight": "N/A", "blood_group": "N/A", "id": p_id or "N/A"}
    if p_id:
        pp_res = await db.execute(select(PatientProfile).where(PatientProfile.user_id == p_id))
        pp = pp_res.scalar_one_or_none()
        if pp:
            patient_data = {
                "name": pp.full_name or "Unknown",
                "age": pp.age or "N/A",
                "sex": pp.sex or "N/A",
                "weight": pp.weight_kg or "N/A",
                "blood_group": pp.blood_group or "N/A",
                "id": pp.patient_id or p_id,
            }

    # Get doctor profile
    dr_res = await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == current_user.id))
    dr = dr_res.scalar_one_or_none()
    doctor_data = {
        "name": f"Dr. {dr.full_name}" if dr else "Dr. Unknown",
        "qualification": dr.qualification if dr else "MBBS",
    }

    prx_id = f"PRX-{uuid.uuid4().hex[:8].upper()}"
    diagnosis_data = {
        "disease": req.disease_confirmed,
        "confidence": sess.top_confidence,
        "severity": "Moderate",
        "symptoms": sess.symptoms_input or [],
        "precautions": req.precautions,
        "dietary_advice": req.dietary_advice,
        "follow_up_days": req.follow_up_days,
    }

    text = rx_generator.generate_prescription(
        prescription_id=prx_id,
        patient_data=patient_data,
        diagnosis_data=diagnosis_data,
        medicines=req.medicines,
        doctor_data=doctor_data,
    )

    prx = Prescription(
        prescription_id=prx_id,
        diagnosis_session_id=sess.id,
        patient_id=p_id,
        doctor_id=current_user.id,
        disease_diagnosed=req.disease_confirmed,
        medicines_prescribed=req.medicines,
        precautions=req.precautions,
        dietary_advice=req.dietary_advice,
        follow_up_date=datetime.utcnow() + timedelta(days=req.follow_up_days),
        llm_generated_text=text,
        status="draft",
    )
    db.add(prx)

    log = DiagnosisAuditLog(
        diagnosis_session_id=sess.id,
        action="prescription_generated",
        performed_by_role="doctor",
        performed_by_id=current_user.id,
        details=f"Prescription {prx_id} generated for {req.disease_confirmed}",
    )
    db.add(log)
    await log_action(db, current_user.id, "prescription_generated", f"session:{sess.session_id}", f"Generated draft for {sess.top_prediction}")
    await db.commit()

    return {"prescription_id": prx_id, "prescription_text": text, "status": "draft"}


@router.put("/prescription/{prescription_id}/approve")
async def approve_prescription(
    prescription_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    if current_user.role != UserRole.doctor:
        raise HTTPException(403, "Only doctors can approve prescriptions")

    res = await db.execute(select(Prescription).where(Prescription.prescription_id == prescription_id))
    prx = res.scalar_one_or_none()
    if not prx:
        raise HTTPException(404, "Prescription not found")

    prx.doctor_approved = True
    prx.status = "approved"
    prx.approved_at = datetime.utcnow()

    # Update diagnosis session status
    sess_res = await db.execute(select(DiagnosisSession).where(DiagnosisSession.id == prx.diagnosis_session_id))
    sess = sess_res.scalar_one_or_none()
    if sess:
        sess.status = "prescribed"

    # Generate PDF
    pdf_bytes = generate_prescription_pdf(
        prescription_text=prx.llm_generated_text or "",
        prescription_id=prescription_id,
    )
    os.makedirs("uploads/prescriptions", exist_ok=True)
    pdf_path = f"uploads/prescriptions/{prescription_id}.pdf"
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    log = DiagnosisAuditLog(
        diagnosis_session_id=prx.diagnosis_session_id,
        action="prescription_approved",
        performed_by_role="doctor",
        performed_by_id=current_user.id,
        details=f"Prescription {prescription_id} approved and PDF generated",
    )
    db.add(log)
    await log_action(db, current_user.id, "prescription_approved", f"session:{sess.session_id}", f"Approved prescription for {sess.top_prediction}")
    await db.commit()

    return {"message": "Prescription approved", "pdf_url": f"/uploads/prescriptions/{prescription_id}.pdf"}


@router.get("/prescription/{prescription_id}")
async def get_prescription(
    prescription_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    res = await db.execute(select(Prescription).where(Prescription.prescription_id == prescription_id))
    prx = res.scalar_one_or_none()
    if not prx:
        raise HTTPException(404, "Prescription not found")

    if current_user.role == UserRole.patient and not prx.doctor_approved:
        raise HTTPException(403, "Prescription not yet approved")

    return {
        "prescription_id": prx.prescription_id,
        "disease_diagnosed": prx.disease_diagnosed,
        "medicines_prescribed": prx.medicines_prescribed,
        "precautions": prx.precautions,
        "dietary_advice": prx.dietary_advice,
        "follow_up_date": prx.follow_up_date.isoformat() if prx.follow_up_date else None,
        "prescription_text": prx.llm_generated_text,
        "status": prx.status,
        "doctor_approved": prx.doctor_approved,
        "created_at": prx.created_at.isoformat(),
    }


@router.get("/prescription/patient/{patient_id}")
async def get_patient_prescriptions(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    q = select(Prescription).where(Prescription.patient_id == patient_id)
    if current_user.role == UserRole.patient:
        q = q.where(Prescription.doctor_approved == True)
    q = q.order_by(desc(Prescription.created_at))
    result = await db.execute(q)
    prxs = result.scalars().all()
    return [{
        "prescription_id": p.prescription_id,
        "disease_diagnosed": p.disease_diagnosed,
        "status": p.status,
        "created_at": p.created_at.isoformat(),
        "doctor_approved": p.doctor_approved,
    } for p in prxs]


# ── Admin Analytics Endpoints ──────────────────────────────

@router.get("/admin/analytics")
async def diagnosis_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total = (await db.execute(select(func.count(DiagnosisSession.id)))).scalar() or 0
    today_count = (await db.execute(
        select(func.count(DiagnosisSession.id)).where(func.date(DiagnosisSession.created_at) == today)
    )).scalar() or 0
    week_count = (await db.execute(
        select(func.count(DiagnosisSession.id)).where(DiagnosisSession.created_at >= week_ago)
    )).scalar() or 0
    month_count = (await db.execute(
        select(func.count(DiagnosisSession.id)).where(DiagnosisSession.created_at >= month_ago)
    )).scalar() or 0

    # Top predicted diseases
    disease_rows = (await db.execute(
        select(DiagnosisSession.top_prediction, func.count(DiagnosisSession.id))
        .group_by(DiagnosisSession.top_prediction)
        .order_by(desc(func.count(DiagnosisSession.id)))
        .limit(10)
    )).all()
    top_diseases = [{
        "disease": r[0], "count": r[1],
        "percentage": round(r[1] / total * 100, 1) if total else 0
    } for r in disease_rows]

    # Diagnosis by role
    role_rows = (await db.execute(
        select(DiagnosisSession.initiated_by, func.count(DiagnosisSession.id))
        .group_by(DiagnosisSession.initiated_by)
    )).all()
    by_role = {r[0]: r[1] for r in role_rows}

    # Prescriptions
    total_rx = (await db.execute(select(func.count(Prescription.id)))).scalar() or 0
    approved_rx = (await db.execute(
        select(func.count(Prescription.id)).where(Prescription.doctor_approved == True)
    )).scalar() or 0

    # Daily trend (last 30 days)
    trend_rows = (await db.execute(
        select(func.date(DiagnosisSession.created_at), func.count(DiagnosisSession.id))
        .where(DiagnosisSession.created_at >= month_ago)
        .group_by(func.date(DiagnosisSession.created_at))
        .order_by(func.date(DiagnosisSession.created_at))
    )).all()
    daily_trend = [{"date": str(r[0]), "count": r[1]} for r in trend_rows]

    return {
        "total_diagnoses": total,
        "diagnoses_today": today_count,
        "diagnoses_this_week": week_count,
        "diagnoses_this_month": month_count,
        "top_predicted_diseases": top_diseases,
        "diagnosis_by_role": by_role,
        "prescriptions_generated": total_rx,
        "prescriptions_approved": approved_rx,
        "daily_trend": daily_trend,
    }


@router.get("/admin/logs")
async def diagnosis_audit_logs(
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    action: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    q = select(DiagnosisAuditLog)
    if action:
        q = q.where(DiagnosisAuditLog.action == action)
    q = q.order_by(desc(DiagnosisAuditLog.created_at)).offset(offset).limit(limit)
    result = await db.execute(q)
    logs = result.scalars().all()
    return [{
        "id": l.id,
        "diagnosis_session_id": l.diagnosis_session_id,
        "action": l.action,
        "performed_by_role": l.performed_by_role,
        "performed_by_id": l.performed_by_id,
        "details": l.details,
        "created_at": l.created_at.isoformat(),
    } for l in logs]

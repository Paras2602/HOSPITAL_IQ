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
from backend.utils.notifications import tts_service, translation_service, email_service
from backend.utils.pdf_generator import generate_prescription_pdf
from backend.utils.logging import log_action
from backend.models.prediction import HealthScore, HealthTimeline

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

class SessionReviewRequest(BaseModel):
    final_diagnosis: str
    doctor_notes: Optional[str] = None
    override_ai: bool = False

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

# Global in-memory cache for patient rate limiting
# Format: {patient_id: [timestamp1, timestamp2, ...]}
PREDICTION_RATE_LIMITS = {}

@router.post("/predict")
async def predict_disease(
    req: DiagnosisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    from backend.utils.security_helpers import validate_symptom_name
    from datetime import datetime, timedelta

    # Rate Limiting Logic (10 requests per hour per patient)
    # Extract patient_id (prioritize req.patient_id or fallback to current_user.id)
    patient_id = req.patient_id or current_user.id
    
    if patient_id:
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        # Initialize list if not exists
        if patient_id not in PREDICTION_RATE_LIMITS:
            PREDICTION_RATE_LIMITS[patient_id] = []
            
        # Clean up timestamps older than 1 hour
        PREDICTION_RATE_LIMITS[patient_id] = [
            ts for ts in PREDICTION_RATE_LIMITS[patient_id] if ts > one_hour_ago
        ]
        
        # Check if limit exceeded
        if len(PREDICTION_RATE_LIMITS[patient_id]) >= 10:
            raise HTTPException(
                status_code=429, 
                detail="Too many prediction requests. Maximum 10 per hour allowed. Please wait before trying again."
            )
            
        # Add current timestamp
        PREDICTION_RATE_LIMITS[patient_id].append(now)

    # A. Minimum symptoms check
    if len(req.symptoms) < 3:
        raise HTTPException(status_code=400, detail="Minimum 3 symptoms required for analysis.")
    
    # B. Maximum symptoms check
    if len(req.symptoms) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 symptoms allowed per request.")

    # D. Regex character stripping/validation
    invalid_chars = [s for s in req.symptoms if not validate_symptom_name(s)]
    if invalid_chars:
        raise HTTPException(status_code=400, detail=f"Invalid characters in symptoms: {invalid_chars}")

    # C. DB Validation
    result = await db.execute(select(Symptom.name).where(Symptom.name.in_(req.symptoms)))
    valid_symptoms = set(result.scalars().all())
    invalid_symptoms = [s for s in req.symptoms if s not in valid_symptoms]
    if invalid_symptoms:
        raise HTTPException(status_code=400, detail=f"Unknown symptoms: {invalid_symptoms}. Please select from the symptom list.")
    
    try:
        # Run prediction (now async)
        prediction = await predictor.predict(req.symptoms)
        
        # Save session
        session_id = f"DX-{uuid.uuid4().hex[:8].upper()}"
        
        # Get top prediction from the new structure
        top_pred = prediction["predictions"][0] if prediction["predictions"] else None
        
        # Get model version from registry
        from backend.ml.model_registry import get_current_version
        current_model_version = get_current_version()
        
        new_session = DiagnosisSession(
            session_id=session_id,
            patient_id=req.patient_id or (current_user.id if current_user.role == UserRole.patient else None),
            initiated_by=req.initiated_by,
            symptoms_input=req.symptoms,
            predicted_diseases=prediction["predictions"],
            top_prediction=top_pred["disease"] if top_pred else "Unknown",
            top_confidence=top_pred["confidence"] if top_pred else 0.0,
            model_version=current_model_version,
            status=prediction["status"] # Use the clinical status from predictor
        )
        
        # Health Advice
        display_name = top_pred["display_name"] if top_pred else "an inconclusive condition"
        if prediction["status"] == "inconclusive":
            prediction["health_advice"] = prediction["message"]
        else:
            prediction["health_advice"] = f"Based on your symptoms, our AI suggests a potential match for {display_name}. {prediction['message']}"
            
        prediction["session_id"] = session_id
        
        db.add(new_session)
        await db.commit()

        # Audit Logs
        audit_log1 = DiagnosisAuditLog(
            diagnosis_session_id=new_session.id,
            action="symptoms_submitted",
            performed_by_role=current_user.role.value if current_user else "patient",
            details=f"Symptoms submitted: {len(req.symptoms)}"
        )
        audit_log2 = DiagnosisAuditLog(
            diagnosis_session_id=new_session.id,
            action="prediction_generated",
            performed_by_role="system",
            details=f"Prediction generated: {top_pred['display_name'] if top_pred else 'Unknown'}"
        )
        audit_log3 = DiagnosisAuditLog(
            diagnosis_session_id=new_session.id,
            action="model_version_used",
            performed_by_role="system",
            details=f"Model version: {current_model_version}"
        )
        db.add_all([audit_log1, audit_log2, audit_log3])
        await db.commit()

        # Item 2: Admin High-Risk Alert
        if top_pred and top_pred["confidence"] > 80 and top_pred.get("severity") in ["Severe", "Critical"]:
            # Fetch patient name
            patient_name = "Unknown Patient"
            if new_session.patient_id:
                p_res = await db.execute(select(User).where(User.id == new_session.patient_id))
                patient_user = p_res.scalar_one_or_none()
                if patient_user:
                    patient_name = patient_user.full_name
            
            # Fetch admin email
            adm_res = await db.execute(select(User.email).where(User.role == "admin"))
            admin_email = adm_res.scalar() or os.getenv("SENDER_EMAIL")
            
            if admin_email:
                email_service.send_email(
                    to_email=admin_email,
                    subject="HIGH RISK ALERT - HospitalIQ",
                    body=f"Patient {patient_name} has {top_pred['display_name']} with {top_pred['confidence']:.1f}% confidence. Severity: {top_pred['severity']}"
                )
            
            # Log in audit
            audit_log = DiagnosisAuditLog(
                diagnosis_session_id=new_session.id,
                action="high_risk_alert_triggered",
                performed_by_role="system",
                details=f"High Risk Alert: {patient_name} - {top_pred['display_name']} ({top_pred['confidence']:.1f}%). Severity: {top_pred['severity']}"
            )
            db.add(audit_log)
            await db.commit()

        # Item 3: Health Score & Timeline Integration
        if new_session.patient_id and top_pred:
            # Get PatientProfile
            pp_res = await db.execute(select(PatientProfile).where(PatientProfile.user_id == new_session.patient_id))
            patient_profile = pp_res.scalar_one_or_none()
            
            if patient_profile:
                # Calculate penalty
                severity_penalty = {
                    "Critical": 15,
                    "Severe": 10,
                    "Moderate": 5,
                    "Mild": 0
                }.get(top_pred.get("severity", "Mild"), 0)
                
                if severity_penalty > 0:
                    # Get latest score record
                    hs_res = await db.execute(
                        select(HealthScore)
                        .where(HealthScore.patient_id == patient_profile.id)
                        .order_by(HealthScore.recorded_at.desc())
                    )
                    latest_hs = hs_res.scalars().first()
                    
                    current_score = latest_hs.score if latest_hs else 100.0
                    new_score = max(0, current_score - severity_penalty)
                    
                    # Create new health score record
                    new_hs = HealthScore(
                        patient_id=patient_profile.id,
                        score=new_score,
                        diabetes_risk=latest_hs.diabetes_risk if latest_hs else 0,
                        heart_risk=latest_hs.heart_risk if latest_hs else 0,
                        ckd_risk=latest_hs.ckd_risk if latest_hs else 0,
                        liver_risk=latest_hs.liver_risk if latest_hs else 0
                    )
                    db.add(new_hs)
                    
                    # Add Timeline Event
                    timeline_event = HealthTimeline(
                        patient_id=patient_profile.id,
                        event_type="diagnosis",
                        title=f"AI Diagnosis: {top_pred['display_name']} detected",
                        details=f"Prediction Confidence: {top_pred['confidence']:.1f}% | Severity: {top_pred['severity']}"
                    )
                    db.add(timeline_event)
                    await db.commit()

        # Strip medicine info for patient-initiated predictions
        if req.initiated_by == "patient":
            for pred in prediction.get("predictions", []):
                pred.pop("recommended_medicines", None)
                pred.pop("medicines", None)

        return prediction
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
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
    # Add audit log
    audit_log = DiagnosisAuditLog(
        diagnosis_session_id=sess.id,
        action="voice_summary_generated",
        performed_by_role="system",
        details=f"Voice summary generated for language: {req.language}"
    )
    db.add(audit_log)
    await db.commit()

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

@router.post("/session/{session_id}/review")
async def review_session(
    session_id: str,
    req: SessionReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(doctor_required)
):
    from backend.utils.security_helpers import sanitize_text
    from datetime import datetime, timedelta

    session = (await db.execute(select(DiagnosisSession).filter_by(session_id=session_id))).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Session Expiry (30 days)
    if datetime.utcnow() - session.created_at > timedelta(days=30):
        raise HTTPException(status_code=410, detail="This diagnosis session has expired after 30 days.")
        
    session.final_diagnosis = sanitize_text(req.final_diagnosis)
    session.doctor_notes = sanitize_text(req.doctor_notes) if req.doctor_notes else None
    session.status = "reviewed"
    session.reviewed_at = datetime.utcnow()
    
    # Check if they overrode the AI
    if req.final_diagnosis.lower() != session.top_prediction.lower() or req.override_ai:
        action_detail = f"AI Override: {session.top_prediction} -> {req.final_diagnosis}"
        action_name = "doctor_overridden"
    else:
        action_detail = f"AI Confirmed: {req.final_diagnosis}"
        action_name = "doctor_confirmed"

    log1 = DiagnosisAuditLog(
        diagnosis_session_id=session.id,
        action="doctor_reviewed",
        performed_by_role="doctor",
        performed_by_id=current_user.id,
        details="Doctor reviewed the session."
    )
    log2 = DiagnosisAuditLog(
        diagnosis_session_id=session.id,
        action=action_name,
        performed_by_role="doctor",
        performed_by_id=current_user.id,
        details=action_detail
    )
    db.add_all([log1, log2])
    await db.commit()
    return {"message": "Session reviewed successfully", "final_diagnosis": session.final_diagnosis}

@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    from datetime import datetime, timedelta

    session = (await db.execute(select(DiagnosisSession).filter_by(session_id=session_id))).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Session Expiry (30 days)
    if datetime.utcnow() - session.created_at > timedelta(days=30):
        raise HTTPException(status_code=410, detail="This diagnosis session has expired after 30 days.")

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

class MedicinePrescriptionSchema(BaseModel):
    name: str
    dosage: str
    frequency: str
    duration: Optional[str] = "5 Days"
    instructions: Optional[str] = ""

class PrescriptionGenerateRequest(BaseModel):
    diagnosis_session_id: str
    patient_id: Optional[str] = None
    disease_confirmed: str
    medicines: List[MedicinePrescriptionSchema]
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

    # 1. Confidence Threshold Enforcement
    confidence = sess.top_confidence
    if confidence < 70:
        raise HTTPException(400, f"Confidence too low for prescription. Minimum 70% required (Found {confidence:.1f}%). Please consult doctor for manual diagnosis.")
    
    low_confidence_warning = False
    if 70 <= confidence < 80:
        low_confidence_warning = True

    # 2. Disease-Medicine Mapping Validation
    from backend.models.symptom_models import Disease, DiseaseMedicineMapping, Medicine
    # Get disease ID from confirmed name
    d_res = await db.execute(select(Disease.id).where(Disease.name == req.disease_confirmed))
    d_id = d_res.scalar()
    if d_id:
        # Get allowed medicines for this disease
        m_res = await db.execute(
            select(Medicine.name)
            .join(DiseaseMedicineMapping, Medicine.id == DiseaseMedicineMapping.medicine_id)
            .where(DiseaseMedicineMapping.disease_id == d_id)
        )
        allowed_medicines = [m[0].lower() for m in m_res.all()]
        
        if not allowed_medicines:
             raise HTTPException(400, f"No medicines mapped for disease '{req.disease_confirmed}'. Doctor must manually select medicines via manual assessment.")

        for med in req.medicines:
            if med.name.lower() not in allowed_medicines:
                raise HTTPException(400, f"Medicine '{med.name}' is not clinically mapped to {req.disease_confirmed}. Please use a mapped medicine.")
    
    # 3. Symptom Compatibility Check
    compatibility = await predictor.check_symptom_compatibility(sess.symptoms_input, req.disease_confirmed)
    symptom_warning = not compatibility["is_compatible"]

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
        "registration_number": dr.registration_number if dr and hasattr(dr, "registration_number") else "REG-772810",
        "contact": dr.phone if dr else "N/A",
    }

    prx_id = f"PRX-{uuid.uuid4().hex[:8].upper()}"
    diagnosis_data = {
        "disease": req.disease_confirmed,
        "confidence": confidence,
        "severity": sess.status if sess.status in ["severe", "critical"] else "Moderate",
        "symptoms": sess.symptoms_input or [],
        "precautions": req.precautions,
        "dietary_advice": req.dietary_advice,
        "follow_up_days": req.follow_up_days,
        "low_confidence_warning": low_confidence_warning,
        "symptom_warning": symptom_warning,
    }

    text = rx_generator.generate_prescription(
        prescription_id=prx_id,
        patient_data=patient_data,
        diagnosis_data=diagnosis_data,
        medicines=[m.dict() for m in req.medicines],
        doctor_data=doctor_data,
    )

    new_prescription = Prescription(
        prescription_id=prx_id,
        diagnosis_session_id=sess.id,
        patient_id=p_id,
        doctor_id=current_user.id,
        disease_diagnosed=req.disease_confirmed,
        medicines_prescribed=[m.model_dump() for m in req.medicines],
        precautions=req.precautions or "",
        dietary_advice=req.dietary_advice or "",
        follow_up_date=datetime.utcnow() + timedelta(days=req.follow_up_days),
        llm_generated_text=text,
        status="draft",
    )
    db.add(new_prescription)

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

    # Generate PDF with structured data
    # Fetch profiles for PDF
    p_profile_res = await db.execute(select(PatientProfile).where(PatientProfile.user_id == prx.patient_id))
    p_profile = p_profile_res.scalar_one_or_none()
    
    dr_profile_res = await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == prx.doctor_id))
    dr_profile = dr_profile_res.scalar_one_or_none()
    
    dr_user_res = await db.execute(select(User).where(User.id == prx.doctor_id))
    dr_user = dr_user_res.scalar_one_or_none()

    pdf_data = {
        "prescription_id": prescription_id,
        "disease": prx.disease_diagnosed,
        "severity": sess.status if sess else "Moderate",
        "medicines": prx.medicines_prescribed,
        "precautions": prx.precautions,
        "dietary_advice": prx.dietary_advice,
        "patient": {
            "name": p_profile.full_name if p_profile else "Unknown",
            "age": p_profile.age if p_profile else "N/A",
            "sex": p_profile.sex if p_profile else "N/A",
            "id": p_profile.patient_id if p_profile else prx.patient_id
        },
        "doctor": {
            "name": dr_profile.full_name if dr_profile else "Doctor",
            "qualification": dr_profile.qualification if dr_profile else "MBBS",
            "registration_number": dr_profile.registration_number if dr_profile else "REG-772810",
            "contact": dr_user.phone if dr_user else "HospitalIQ"
        }
    }

    pdf_bytes = generate_prescription_pdf(prescription_data=pdf_data)
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
    
    # Send Notification to Patient
    try:
        from backend.utils.notifications import email_service
        p_res = await db.execute(select(User.email, User.name).where(User.id == sess.patient_id))
        p_user = p_res.first()
        if p_user:
            p_email, p_name = p_user
            email_service.send_email(
                to_email=p_email,
                subject=f"Prescription Ready — {sess.top_prediction}",
                body=f"Dear {p_name}, your prescription for {sess.top_prediction} has been approved by Dr. {current_user.name}. You can view and download it from your dashboard."
            )
    except Exception as e:
        print(f"Prescription notification error: {e}")

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
    
@router.get("/prescription/{prescription_id}/pdf")
async def get_prescription_pdf(
    prescription_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    res = await db.execute(select(Prescription).where(Prescription.prescription_id == prescription_id))
    prx = res.scalar_one_or_none()
    if not prx:
        raise HTTPException(404, "Prescription not found")

    # Authorization
    if current_user.role == UserRole.patient and prx.patient_id != current_user.id:
        raise HTTPException(403, "Access denied")
    if current_user.role == UserRole.doctor and prx.doctor_id != current_user.id:
        raise HTTPException(403, "Access denied")

    pdf_path = f"uploads/prescriptions/{prescription_id}.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(404, "PDF file not found")

    # Add audit log
    audit_log = DiagnosisAuditLog(
        diagnosis_session_id=prx.diagnosis_session_id,
        action="prescription_downloaded",
        performed_by_role=current_user.role.value if current_user else "unknown",
        performed_by_id=current_user.id,
        details=f"Downloaded prescription PDF {prescription_id}"
    )
    db.add(audit_log)
    await db.commit()

    from fastapi.responses import FileResponse
    return FileResponse(pdf_path, media_type='application/pdf', filename=f"Prescription-{prescription_id}.pdf")


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
        "medicines_prescribed": p.medicines_prescribed or [],
        "created_at": p.created_at.isoformat(),
        "approved_at": p.approved_at.isoformat() if p.approved_at else p.created_at.isoformat(),
        "doctor_approved": p.doctor_approved,
    } for p in prxs]

@router.get("/prescription/doctor/{doctor_id}")
async def get_doctor_prescriptions(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    # Authorization check
    is_admin = current_user.role == UserRole.admin
    is_target_doctor = current_user.role == UserRole.doctor and current_user.id == doctor_id

    if not is_admin and not is_target_doctor:
        raise HTTPException(status_code=403, detail="Not authorized to access this doctor's prescriptions")

    result = await db.execute(
        select(Prescription, PatientProfile.full_name.label("patient_name"))
        .join(PatientProfile, Prescription.patient_id == PatientProfile.user_id, isouter=True)
        .where(Prescription.doctor_id == doctor_id)
        .order_by(desc(Prescription.created_at))
    )
    
    rows = result.all()
    return [{
        "prescription_id": p.prescription_id,
        "patient_name": name or "Unknown Patient",
        "disease_diagnosed": p.disease_diagnosed,
        "status": p.status,
        "created_at": p.created_at.isoformat(),
        "doctor_approved": p.doctor_approved,
    } for p, name in rows]


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


@router.get("/model-info")
async def get_model_info(current_user: User = Depends(authenticated)):
    """Returns current ML model version, training date, accuracy metrics, and coverage."""
    from backend.ml.model_registry import get_current_model_info
    info = get_current_model_info()
    return {
        "model_version": info.get("version", "v1.0"),
        "trained_at": info.get("trained_at", "Unknown"),
        "accuracy": info.get("accuracy", 0.0),
        "f1_score": info.get("f1_score", 0.0),
        "auc_score": info.get("auc_score", 0.0),
        "diseases_covered": info.get("diseases_covered", 0),
        "symptoms_supported": info.get("symptoms_used", 0),
        "model_type": info.get("parameters", {}).get("model_type", "RandomForestClassifier"),
    }

@router.get("/admin/export")
async def export_diagnoses_csv(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from datetime import datetime
    
    q = select(DiagnosisSession)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            q = q.where(DiagnosisSession.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
            
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            q = q.where(DiagnosisSession.created_at < end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
            
    q = q.order_by(desc(DiagnosisSession.created_at))
    result = await db.execute(q)
    sessions = result.scalars().all()
    
    patient_ids = [s.patient_id for s in sessions if s.patient_id]
    users_map = {}
    if patient_ids:
        user_res = await db.execute(select(User).where(User.id.in_(patient_ids)))
        users_map = {u.id: u.full_name for u in user_res.scalars().all()}
        
    session_ids = [s.id for s in sessions]
    rx_sessions = set()
    if session_ids:
        rx_res = await db.execute(select(Prescription.diagnosis_session_id).where(Prescription.diagnosis_session_id.in_(session_ids)))
        rx_sessions = set(rx_res.scalars().all())
        
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "session_id", "patient_id", "patient_name", "date",
        "symptoms_count", "symptoms_list", "top_prediction",
        "confidence", "severity", "status", "doctor_id",
        "doctor_review_status", "prescription_created", "created_at"
    ])
    
    for s in sessions:
        patient_name = users_map.get(s.patient_id, "Unknown") if s.patient_id else "Unknown"
        symptoms_list = ", ".join(s.symptoms_input) if isinstance(s.symptoms_input, list) else str(s.symptoms_input)
        
        # Determine severity from predicted_diseases
        severity = "Unknown"
        if s.predicted_diseases and isinstance(s.predicted_diseases, list) and len(s.predicted_diseases) > 0:
            severity = s.predicted_diseases[0].get("severity", "Unknown")
            
        writer.writerow([
            s.session_id,
            s.patient_id or "",
            patient_name,
            s.created_at.strftime("%Y-%m-%d"),
            len(s.symptoms_input) if isinstance(s.symptoms_input, list) else 0,
            symptoms_list,
            s.top_prediction,
            f"{s.top_confidence:.2f}",
            severity,
            s.status,
            s.doctor_id or "",
            "Reviewed" if s.status == "reviewed" else "Pending",
            "Yes" if s.id in rx_sessions else "No",
            s.created_at.isoformat()
        ])
        
    output.seek(0)
    current_date = datetime.utcnow().strftime("%Y%m%d")
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=hospitaliq_diagnoses_{current_date}.csv"}
    )

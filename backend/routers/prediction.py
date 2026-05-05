from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import json
from backend.database import get_db
from backend.models.user import User, UserRole
from backend.models.patient import PatientProfile
from backend.models.prediction import PredictionRecord, HealthScore
from backend.utils.deps import get_current_user
from backend.utils.logging import log_action

router = APIRouter(prefix="/predict", tags=["prediction"])

SUPPORTED_DISEASES = {"diabetes", "heart", "ckd", "liver"}


class PredictRequest(BaseModel):
    patient_profile_id: str
    disease: str
    input_features: dict


@router.post("/{disease}")
async def run_prediction(
    disease: str,
    req: PredictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    disease = disease.lower()
    if disease not in SUPPORTED_DISEASES:
        raise HTTPException(status_code=400, detail=f"Unsupported disease. Choose: {SUPPORTED_DISEASES}")

    # Verify patient
    pp_result = await db.execute(
        select(PatientProfile).where(PatientProfile.id == req.patient_profile_id)
    )
    pp = pp_result.scalar_one_or_none()
    if not pp:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Run ML
    try:
        from backend.ml.predict import predict
        result = predict(disease, req.input_features)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

    # Save record
    record = PredictionRecord(
        patient_id=req.patient_profile_id,
        requested_by=current_user.id,
        disease=disease,
        input_features=json.dumps(req.input_features),
        risk_probability=result["risk_probability"],
        risk_label=result["risk_label"],
        shap_values=json.dumps(result["shap_values"]),
        lime_explanation=json.dumps(result["lime_explanation"]),
        recommendations=result["recommendations"],
        model_version=result["model_version"],
    )
    db.add(record)

    # Update health score
    await _update_health_score(db, req.patient_profile_id, disease, result["risk_probability"])
    
    await log_action(db, current_user.id, "predict", f"disease:{disease}", f"Risk: {result['risk_label']} ({result['risk_probability']:.2f})")
    await db.commit()

    return {
        "prediction_id": record.id,
        "disease": disease,
        **result,
    }


@router.post("/whatif/{disease}")
async def whatif_simulation(
    disease: str,
    req: PredictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """What-if simulation — no DB save, just prediction."""
    disease = disease.lower()
    if disease not in SUPPORTED_DISEASES:
        raise HTTPException(status_code=400, detail="Unsupported disease")
    try:
        from backend.ml.predict import predict
        result = predict(disease, req.input_features)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    await log_action(db, current_user.id, "predict_whatif", f"disease:{disease}", "Ran what-if simulation")
    await db.commit()
    return result

@router.get("/history/{patient_profile_id}")
async def get_history(
    patient_profile_id: str,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch the patient profile requested
    pp_result = await db.execute(select(PatientProfile).where(PatientProfile.id == patient_profile_id))
    pp_requested = pp_result.scalar_one_or_none()
    if not pp_requested:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    # Authorization check:
    # 1. Admins can access any history.
    # 2. Patients can access their own history.
    # 3. Doctors can access history for patients they are associated with (this part requires relationship logic not fully present yet, so for now, doctors might have broader access or need explicit patient consent/sharing mechanisms).
    # For simplicity in this iteration, we'll allow Admins, and Patients to see their own data.
    # A doctor should ideally check against a patient they are currently attending or have been assigned.

    is_admin = current_user.role == UserRole.admin
    is_patient_owner = current_user.id == pp_requested.user_id # Check if the current user is the owner of the profile

    # If not admin and not the patient owner, deny access.
    # Doctors are currently allowed by 'get_current_user', but lack specific patient association logic here.
    # Refinement: If current_user.role == UserRole.doctor, we'd need to check if this doctor is associated with pp_requested.patient_id.
    # For now, let's restrict to Patient and Admin for direct access.
    if not is_admin and not is_patient_owner:
        raise HTTPException(status_code=403, detail="Not authorized to access this patient's prediction history")

    result = await db.execute(
        select(PredictionRecord)
        .where(PredictionRecord.patient_id == patient_profile_id)
        .order_by(desc(PredictionRecord.created_at))
        .offset(offset).limit(limit)
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


@router.get("/features/{disease}")
async def get_disease_features(disease: str):
    """Return required features for a disease model."""
    import os, json
    from backend.ml.predict import MODEL_DIR
    meta_path = os.path.join(MODEL_DIR, f"{disease}_meta.json")
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="Model not found — train models first")
    with open(meta_path) as f:
        meta = json.load(f)
    return meta


async def _update_health_score(db, patient_id: str, disease: str, risk: float):
    result = await db.execute(
        select(HealthScore).where(HealthScore.patient_id == patient_id)
        .order_by(HealthScore.recorded_at.desc()).limit(1)
    )
    latest = result.scalar_one_or_none()

    risks = {
        "diabetes_risk": latest.diabetes_risk if latest else None,
        "heart_risk": latest.heart_risk if latest else None,
        "ckd_risk": latest.ckd_risk if latest else None,
        "liver_risk": latest.liver_risk if latest else None,
    }
    risks[f"{disease}_risk"] = risk

    known = [v for v in risks.values() if v is not None]
    score = round(100 - (sum(known) / max(len(known), 1)) * 100, 1)

    hs = HealthScore(patient_id=patient_id, score=score, **risks)
    db.add(hs)

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import io
from backend.database import get_db
from backend.models.user import User
from backend.models.patient import PatientProfile
from backend.models.prediction import PredictionRecord
from backend.utils.deps import get_current_user
from backend.utils.pdf_generator import generate_pdf_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/pdf/{prediction_id}")
async def download_pdf_report(
    prediction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pred_result = await db.execute(
        select(PredictionRecord).where(PredictionRecord.id == prediction_id)
    )
    pred = pred_result.scalar_one_or_none()
    if not pred:
        return JSONResponse(status_code=404, content={"detail": "Prediction not found"})

    pp_result = await db.execute(
        select(PatientProfile).where(PatientProfile.id == pred.patient_id)
    )
    pp = pp_result.scalar_one_or_none()
    patient_data = {
        "patient_id": pp.patient_id if pp else "—",
        "full_name": pp.full_name if pp else "—",
        "age": pp.age if pp else None,
        "sex": pp.sex if pp else "—",
        "blood_group": pp.blood_group if pp else "—",
        "height_cm": pp.height_cm if pp else None,
        "weight_kg": pp.weight_kg if pp else None,
        "allergies": pp.allergies if pp else "—",
        "chronic_conditions": pp.chronic_conditions if pp else "—",
    }

    import json, base64, os
    shap_vals = {}
    shap_b64 = None
    lime_exp = {}
    try:
        shap_vals = json.loads(pred.shap_values or "{}")
        lime_exp = json.loads(pred.lime_explanation or "{}")
        # Re-generate SHAP plot for PDF
        input_features = json.loads(pred.input_features or "{}")
        from backend.ml.predict import predict
        fresh = predict(pred.disease, input_features)
        shap_b64 = fresh.get("shap_plot_base64")
    except Exception:
        pass

    prediction_data = {
        "disease": pred.disease,
        "risk_probability": pred.risk_probability,
        "risk_percent": pred.risk_probability * 100,
        "risk_label": pred.risk_label,
        "shap_values": shap_vals,
        "shap_plot_base64": shap_b64,
        "lime_explanation": lime_exp,
        "recommendations": pred.recommendations,
        "model_version": pred.model_version,
    }

    report_url = f"https://hospitaliq.app/reports/{prediction_id}"
    pdf_bytes = generate_pdf_report(patient_data, prediction_data, report_url=report_url)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=HospitalIQ_Report_{prediction_id[:8]}.pdf"
        },
    )


@router.get("/voice/{prediction_id}")
async def get_voice_summary(
    prediction_id: str,
    lang: str = "en",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pred_result = await db.execute(
        select(PredictionRecord).where(PredictionRecord.id == prediction_id)
    )
    pred = pred_result.scalar_one_or_none()
    if not pred:
        return JSONResponse(status_code=404, content={"detail": "Prediction not found"})

    text = (
        f"Health report for {pred.disease} disease. "
        f"Your risk level is {pred.risk_label}. "
        f"Risk probability is {pred.risk_probability * 100:.1f} percent. "
        f"{pred.recommendations or ''}"
    )

    try:
        from gtts import gTTS
        tts = gTTS(text, lang=lang)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=voice_summary.mp3"},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Voice generation failed: {e}"})

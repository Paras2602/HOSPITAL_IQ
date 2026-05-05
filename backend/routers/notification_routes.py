"""
============================================
HospitalIQ — Notification API Routes
============================================

Exposes REST endpoints for email, TTS, translation,
and QR code services.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import re # For filename sanitization
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker  # Import AsyncSession

from backend.utils.notifications import (
    email_service,
    tts_service,
    translation_service,
    qr_service,
    AUDIO_DIR,
    QRCODE_DIR,
)
from backend.utils.deps import get_current_user, require_role
from backend.models.user import User, UserRole
from backend.database import get_db # Import the get_db function

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

# Define rate limiting parameters (example values, can be adjusted)
# Consider using a library like 'fastapi-limiter' for more robust implementation
RATE_LIMIT_PER_MINUTE = 10 


# ============================================
#  REQUEST SCHEMAS
# ============================================
class EmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    html: bool = False


class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    filename: Optional[str] = None


class TranslateRequest(BaseModel):
    text: str
    target_language: str = "hi"


class QRRequest(BaseModel):
    data: str
    filename: Optional[str] = None
    fill_color: str = "black"
    back_color: str = "white"


class ReportQRRequest(BaseModel):
    report_id: str
    base_url: str = "https://hospitaliq.com"


class PatientQRRequest(BaseModel):
    patient_id: str
    patient_name: str = ""


class AppointmentQRRequest(BaseModel):
    appointment_id: str
    patient_name: str
    doctor_name: str
    date: str
    time: str


# Helper to check if rate limit is exceeded (simplified)
async def check_rate_limit(request: Request, user_id: str, action: str):
    # In a real application, this would involve checking timestamps against a cache/DB
    # For this example, we'll skip actual rate limiting implementation but note its importance.
    pass 

# ============================================
#  EMAIL ENDPOINTS
# ============================================
@router.post("/send-email")
async def send_email(
    req: EmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db), # Added db dependency if needed for user lookup/audit
    current_user: User = Depends(get_current_user), # Authenticate user
):
    """Send a custom email notification. Access may be restricted."""
    # Example role restriction: Allow only admins or specific service accounts to send emails.
    # require_role(UserRole.admin) # Uncomment and adjust role as needed
    
    # Simplified check: Only allow authenticated users for now.
    # More specific role checks or originating service checks might be needed.
    
    # Rate limiting check (placeholder)
    await check_rate_limit(request=request, user_id=current_user.id, action="send_email")

    result = email_service.send_email(
        to_email=req.to_email,
        subject=req.subject,
        body=req.body,
        html=req.html,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


# ============================================
#  TTS ENDPOINTS
# ============================================
@router.post("/text-to-speech")
async def text_to_speech(
    req: TTSRequest,
    request: Request,
    current_user: User = Depends(get_current_user), # Authenticate user
):
    """Convert text to speech and return audio file metadata."""
    # Rate limiting check (placeholder)
    await check_rate_limit(request=request, user_id=current_user.id, action="tts")

    result = tts_service.text_to_speech(
        text=req.text,
        language=req.language,
        filename=req.filename,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.get("/download-audio/{filename}")
async def download_audio(filename: str, current_user: User = Depends(get_current_user)): # Authenticate user
    """Download a generated TTS audio file."""
    # Check if the user is authorized to download this file (e.g., based on ownership or role)
    # For now, assuming authenticated user can download if file exists.
    filepath = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        filepath,
        media_type="audio/mpeg",
        filename=filename,
    )


# ============================================
#  TRANSLATION ENDPOINTS
# ============================================
@router.post("/translate")
async def translate(
    req: TranslateRequest,
    request: Request,
    current_user: User = Depends(get_current_user), # Authenticate user
):
    """Translate text to target language."""
    # Rate limiting check (placeholder)
    await check_rate_limit(request=request, user_id=current_user.id, action="translate")

    result = translation_service.translate(
        text=req.text,
        target_language=req.target_language,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.get("/supported-languages")
async def supported_languages():
    """Get list of supported translation languages."""
    # This endpoint is generally public, no authentication needed unless translations are paid/limited.
    return translation_service.get_supported_languages()


# ============================================
#  QR CODE ENDPOINTS
# ============================================
@router.post("/generate-qr")
async def generate_qr(
    req: QRRequest,
    request: Request,
    current_user: User = Depends(get_current_user), # Authenticate user
):
    """Generate a custom QR code."""
    # Rate limiting check (placeholder)
    await check_rate_limit(request=request, user_id=current_user.id, action="generate_qr")

    result = qr_service.generate_qr(
        data=req.data,
        filename=req.filename,
        fill_color=req.fill_color,
        back_color=req.back_color,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/generate-report-qr")
async def generate_report_qr(
    req: ReportQRRequest,
    request: Request,
    current_user: User = Depends(get_current_user), # Authenticate user
):
    """Generate a QR code for a patient report."""
    # Authorization: Check if current_user is authorized for this report_id (e.g., patient owner, doctor, admin)
    # This requires fetching report/patient data and checking relationships.

    # Rate limiting check (placeholder)
    await check_rate_limit(request=request, user_id=current_user.id, action="generate_report_qr")

    result = qr_service.generate_report_qr(
        report_id=req.report_id,
        base_url=req.base_url,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/generate-patient-qr")
async def generate_patient_qr(
    req: PatientQRRequest,
    request: Request,
    current_user: User = Depends(get_current_user), # Authenticate user
):
    """Generate a QR code for patient identification."""
    # Authorization: Check if current_user is the patient or an admin/doctor authorized for this patient_id.
    
    # Rate limiting check (placeholder)
    await check_rate_limit(request=request, user_id=current_user.id, action="generate_patient_qr")

    result = qr_service.generate_patient_id_qr(
        patient_id=req.patient_id,
        patient_name=req.patient_name,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/generate-appointment-qr")
async def generate_appointment_qr(
    req: AppointmentQRRequest,
    request: Request,
    current_user: User = Depends(get_current_user), # Authenticate user
):
    """Generate a QR code for appointment verification."""
    # Authorization: Check if current_user is the patient, doctor, or admin associated with this appointment.
    
    # Rate limiting check (placeholder)
    await check_rate_limit(request=request, user_id=current_user.id, action="generate_appointment_qr")

    result = qr_service.generate_appointment_qr(
        appointment_id=req.appointment_id,
        patient_name=req.patient_name,
        doctor_name=req.doctor_name,
        date=req.date,
        time=req.time,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.get("/download-qr/{filename}")
async def download_qr(filename: str, current_user: User = Depends(get_current_user)): # Authenticate user
    """Download a generated QR code image."""
    # Authorization: Check if the user is allowed to download this QR code.
    # This might depend on which QR code was generated and for whom.
    
    filepath = os.path.join(QRCODE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="QR code file not found")
    return FileResponse(
        filepath,
        media_type="image/png",
        filename=filename,
    )

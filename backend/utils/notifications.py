"""
============================================
HospitalIQ — Notification Utility Services
============================================

Provides four core utility services:
  1. EmailService       — SMTP-based email notifications
  2. TTSService         — Text-to-Speech via gTTS
  3. TranslationService — Multi-language translation via googletrans
  4. QRCodeService      — QR code generation via qrcode library

All services read configuration from environment variables.
"""

import os
import smtplib
import logging
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, List

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("hospitaliq.notifications")


# ============================================
#  UPLOAD DIRECTORY SETUP
# ============================================
UPLOAD_BASE = os.path.join(os.getcwd(), "uploads")
AUDIO_DIR = os.path.join(UPLOAD_BASE, "audio")
QRCODE_DIR = os.path.join(UPLOAD_BASE, "qrcodes")
REPORTS_DIR = os.path.join(UPLOAD_BASE, "reports")

for _d in [AUDIO_DIR, QRCODE_DIR, REPORTS_DIR]:
    os.makedirs(_d, exist_ok=True)


# ============================================
#  1. EMAIL SERVICE
# ============================================
class EmailService:
    """SMTP-based email notification service for HospitalIQ."""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "hospitaliq.notify@gmail.com")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.hospital_name = os.getenv("HOSPITAL_NAME", "HospitalIQ")

    # ------------------------------------------
    #  Core send method
    # ------------------------------------------
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
    ) -> Dict:
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            body: Email body (plain text or HTML).
            html: If True, body is treated as HTML.

        Returns:
            dict with status and message.
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.hospital_name} <{self.sender_email}>"
            msg["To"] = to_email

            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(f"✅ Email sent to {to_email}: {subject}")
            return {"status": "success", "message": f"Email sent to {to_email}"}

        except smtplib.SMTPAuthenticationError:
            logger.error("❌ SMTP authentication failed — check SENDER_PASSWORD in .env")
            return {"status": "error", "message": "SMTP authentication failed. Check credentials."}
        except Exception as e:
            logger.error(f"❌ Email send failed: {e}")
            return {"status": "error", "message": str(e)}

    # ------------------------------------------
    #  Convenience: Welcome email
    # ------------------------------------------
    def send_welcome_email(self, to_email: str, patient_name: str) -> Dict:
        """Send a welcome email after patient registration."""
        subject = f"Welcome to {self.hospital_name}! 🏥"
        body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#222;">
        <div style="max-width:600px;margin:auto;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
            <div style="background:linear-gradient(135deg,#0ea5e9,#6366f1);padding:24px;color:#fff;text-align:center;">
                <h1 style="margin:0;">🏥 {self.hospital_name}</h1>
            </div>
            <div style="padding:24px;">
                <h2>Welcome, {patient_name}!</h2>
                <p>Your account has been created successfully. You now have access to:</p>
                <ul>
                    <li>📋 <b>AI-Powered Disease Prediction</b></li>
                    <li>📊 <b>Personalized Health Reports</b></li>
                    <li>📅 <b>Appointment Booking</b></li>
                    <li>🧪 <b>Lab Results Tracking</b></li>
                </ul>
                <p>Thank you for choosing {self.hospital_name}.</p>
                <p style="color:#888;font-size:12px;">This is an automated message. Do not reply.</p>
            </div>
        </div>
        </body></html>
        """
        return self.send_email(to_email, subject, body, html=True)

    # ------------------------------------------
    #  Convenience: Appointment confirmation
    # ------------------------------------------
    def send_appointment_confirmation(
        self,
        to_email: str,
        patient_name: str,
        doctor_name: str,
        date: str,
        time: str,
        token_no: Optional[int] = None,
    ) -> Dict:
        """Send appointment confirmation email."""
        token_line = f"<p><b>Token No:</b> {token_no}</p>" if token_no else ""
        subject = f"Appointment Confirmed — {self.hospital_name}"
        body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#222;">
        <div style="max-width:600px;margin:auto;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
            <div style="background:linear-gradient(135deg,#10b981,#0ea5e9);padding:24px;color:#fff;text-align:center;">
                <h1 style="margin:0;">📅 Appointment Confirmed</h1>
            </div>
            <div style="padding:24px;">
                <p>Dear <b>{patient_name}</b>,</p>
                <p>Your appointment has been confirmed with the following details:</p>
                <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                    <tr><td style="padding:8px;border:1px solid #e0e0e0;"><b>Doctor</b></td><td style="padding:8px;border:1px solid #e0e0e0;">Dr. {doctor_name}</td></tr>
                    <tr><td style="padding:8px;border:1px solid #e0e0e0;"><b>Date</b></td><td style="padding:8px;border:1px solid #e0e0e0;">{date}</td></tr>
                    <tr><td style="padding:8px;border:1px solid #e0e0e0;"><b>Time</b></td><td style="padding:8px;border:1px solid #e0e0e0;">{time}</td></tr>
                </table>
                {token_line}
                <p>Please arrive <b>15 minutes early</b> for check-in.</p>
                <p style="color:#888;font-size:12px;">— {self.hospital_name} Team</p>
            </div>
        </div>
        </body></html>
        """
        return self.send_email(to_email, subject, body, html=True)

    # ------------------------------------------
    #  Convenience: Lab report ready
    # ------------------------------------------
    def send_lab_report_ready(
        self, to_email: str, patient_name: str, report_id: str
    ) -> Dict:
        """Notify patient that lab report is ready."""
        subject = f"Lab Report Ready — {self.hospital_name}"
        body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#222;">
        <div style="max-width:600px;margin:auto;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
            <div style="background:linear-gradient(135deg,#8b5cf6,#ec4899);padding:24px;color:#fff;text-align:center;">
                <h1 style="margin:0;">🧪 Lab Report Ready</h1>
            </div>
            <div style="padding:24px;">
                <p>Dear <b>{patient_name}</b>,</p>
                <p>Your lab report <b>(#{report_id})</b> is now available.</p>
                <p>Please log in to your {self.hospital_name} dashboard to view the full results.</p>
                <p style="color:#888;font-size:12px;">— {self.hospital_name} Team</p>
            </div>
        </div>
        </body></html>
        """
        return self.send_email(to_email, subject, body, html=True)

    # ------------------------------------------
    #  Convenience: Risk alert
    # ------------------------------------------
    def send_risk_alert(
        self,
        to_email: str,
        patient_name: str,
        disease: str,
        risk_level: str,
        risk_percentage: float,
    ) -> Dict:
        """Send high-risk alert notification."""
        color = "#ef4444" if risk_level.lower() == "high" else "#f59e0b"
        subject = f"⚠️ {risk_level.upper()} Risk Alert — {disease} — {self.hospital_name}"
        body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#222;">
        <div style="max-width:600px;margin:auto;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
            <div style="background:{color};padding:24px;color:#fff;text-align:center;">
                <h1 style="margin:0;">⚠️ {risk_level.upper()} Risk Detected</h1>
            </div>
            <div style="padding:24px;">
                <p>Dear <b>{patient_name}</b>,</p>
                <p>Our AI analysis has detected a <b style="color:{color};">{risk_level.upper()}</b> risk
                   for <b>{disease}</b> at <b>{risk_percentage:.1f}%</b>.</p>
                <p>We strongly recommend scheduling an appointment with your doctor immediately.</p>
                <p style="color:#888;font-size:12px;">— {self.hospital_name} Clinical AI Team</p>
            </div>
        </div>
        </body></html>
        """
        return self.send_email(to_email, subject, body, html=True)

    # ------------------------------------------
    #  Convenience: Access code
    # ------------------------------------------
    def send_access_code(self, to_email: str, code: str, purpose: str = "login") -> Dict:
        """Send an OTP / access code email."""
        subject = f"Your Access Code — {self.hospital_name}"
        body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#222;">
        <div style="max-width:600px;margin:auto;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
            <div style="background:linear-gradient(135deg,#0ea5e9,#6366f1);padding:24px;color:#fff;text-align:center;">
                <h1 style="margin:0;">🔐 Access Code</h1>
            </div>
            <div style="padding:24px;text-align:center;">
                <p>Your {purpose} code is:</p>
                <div style="font-size:32px;font-weight:bold;letter-spacing:8px;padding:16px;background:#f1f5f9;border-radius:8px;display:inline-block;margin:16px 0;">
                    {code}
                </div>
                <p style="color:#888;font-size:12px;">This code expires in 10 minutes. Do not share it with anyone.</p>
            </div>
        </div>
        </body></html>
        """
        return self.send_email(to_email, subject, body, html=True)


# ============================================
#  2. TEXT-TO-SPEECH (TTS) SERVICE
# ============================================
class TTSService:
    """Google Text-to-Speech service for converting text to audio."""

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "hi": "Hindi",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada",
        "ml": "Malayalam",
        "bn": "Bengali",
        "mr": "Marathi",
        "gu": "Gujarati",
        "ur": "Urdu",
    }

    # ------------------------------------------
    #  Core TTS
    # ------------------------------------------
    def text_to_speech(
        self,
        text: str,
        language: str = "en",
        filename: Optional[str] = None,
    ) -> Dict:
        """
        Convert text to an MP3 audio file.

        Args:
            text: The text to speak.
            language: BCP-47 language code (default: 'en').
            filename: Custom output filename. Auto-generated if omitted.

        Returns:
            dict with filepath and status.
        """
        try:
            from gtts import gTTS

            if not filename:
                filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"

            filepath = os.path.join(AUDIO_DIR, filename)

            tts = gTTS(text=text, lang=language, slow=False)
            tts.save(filepath)

            logger.info(f"🔊 TTS audio saved: {filepath}")
            return {
                "status": "success",
                "filepath": filepath,
                "filename": filename,
                "url": f"/uploads/audio/{filename}",
            }
        except Exception as e:
            logger.error(f"❌ TTS failed: {e}")
            return {"status": "error", "message": str(e)}

    # ------------------------------------------
    #  Prediction audio
    # ------------------------------------------
    def generate_prediction_audio(
        self,
        disease: str,
        risk_level: str,
        risk_percentage: float,
        recommendations: str = "",
        language: str = "en",
    ) -> Dict:
        """Generate a spoken summary of a prediction result."""
        text = (
            f"Your {disease} risk assessment is complete. "
            f"The risk level is {risk_level} at {risk_percentage:.1f} percent. "
        )
        if recommendations:
            text += f"Recommendations: {recommendations}"
        else:
            text += "Please consult your doctor for personalised advice."

        filename = f"prediction_{disease}_{uuid.uuid4().hex[:6]}.mp3"
        return self.text_to_speech(text, language=language, filename=filename)

    # ------------------------------------------
    #  Report audio
    # ------------------------------------------
    def generate_report_audio(
        self,
        report_text: str,
        report_id: str,
        language: str = "en",
    ) -> Dict:
        """Generate audio narration of a health report."""
        filename = f"report_{report_id}_{uuid.uuid4().hex[:6]}.mp3"
        return self.text_to_speech(report_text, language=language, filename=filename)


# ============================================
#  3. TRANSLATION SERVICE
# ============================================
class TranslationService:
    """Multi-language translation service powered by Google Translate (via deep-translator)."""

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "hi": "Hindi (हिंदी)",
        "ta": "Tamil (தமிழ்)",
        "te": "Telugu (తెలుగు)",
        "kn": "Kannada (ಕನ್ನಡ)",
        "ml": "Malayalam (മലയാളം)",
        "bn": "Bengali (বাংলা)",
        "mr": "Marathi (मराठी)",
        "gu": "Gujarati (ગુજરાતી)",
        "ur": "Urdu (اردو)",
        "fr": "French",
        "es": "Spanish",
        "de": "German",
        "ar": "Arabic",
        "zh-CN": "Chinese (Simplified)",
        "ja": "Japanese",
    }

    # ------------------------------------------
    #  Core translate
    # ------------------------------------------
    def translate(self, text: str, target_language: str = "hi") -> Dict:
        """
        Translate text to the target language.

        Args:
            text: Source text (auto-detected language).
            target_language: Target language code.

        Returns:
            dict with translated text, source language, and target language.
        """
        try:
            from deep_translator import GoogleTranslator

            translator = GoogleTranslator(source="auto", target=target_language)
            translated = translator.translate(text)

            return {
                "status": "success",
                "original": text,
                "translated": translated,
                "source_language": "auto",
                "target_language": target_language,
            }
        except Exception as e:
            logger.error(f"❌ Translation failed: {e}")
            return {"status": "error", "message": str(e)}

    # ------------------------------------------
    #  Translate prediction result
    # ------------------------------------------
    def translate_prediction_result(
        self,
        disease: str,
        risk_level: str,
        risk_percentage: float,
        recommendations: str,
        target_language: str = "hi",
    ) -> Dict:
        """Translate a structured prediction result."""
        text = (
            f"Disease: {disease}. "
            f"Risk Level: {risk_level}. "
            f"Risk: {risk_percentage:.1f}%. "
            f"Recommendations: {recommendations}"
        )
        return self.translate(text, target_language)

    # ------------------------------------------
    #  Supported languages
    # ------------------------------------------
    def get_supported_languages(self) -> Dict:
        """Return the list of supported translation languages."""
        return {
            "status": "success",
            "languages": self.SUPPORTED_LANGUAGES,
            "count": len(self.SUPPORTED_LANGUAGES),
        }


# ============================================
#  4. QR CODE SERVICE
# ============================================
class QRCodeService:
    """QR code generation service for reports, IDs, and appointments."""

    # ------------------------------------------
    #  Core QR generator
    # ------------------------------------------
    def generate_qr(
        self,
        data: str,
        filename: Optional[str] = None,
        fill_color: str = "black",
        back_color: str = "white",
        box_size: int = 10,
        border: int = 4,
    ) -> Dict:
        """
        Generate a QR code PNG image.

        Args:
            data: Content to encode in the QR code.
            filename: Custom output filename. Auto-generated if omitted.
            fill_color: Foreground colour.
            back_color: Background colour.
            box_size: Size of each QR module in pixels.
            border: Border width in modules.

        Returns:
            dict with filepath and status.
        """
        try:
            import qrcode

            if not filename:
                filename = f"qr_{uuid.uuid4().hex[:8]}.png"

            filepath = os.path.join(QRCODE_DIR, filename)

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=box_size,
                border=border,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color=fill_color, back_color=back_color)
            img.save(filepath)

            logger.info(f"📱 QR code saved: {filepath}")
            return {
                "status": "success",
                "filepath": filepath,
                "filename": filename,
                "url": f"/uploads/qrcodes/{filename}",
            }
        except Exception as e:
            logger.error(f"❌ QR generation failed: {e}")
            return {"status": "error", "message": str(e)}

    # ------------------------------------------
    #  Report QR
    # ------------------------------------------
    def generate_report_qr(self, report_id: str, base_url: str = "https://hospitaliq.com") -> Dict:
        """Generate a QR code linking to a report."""
        data = f"{base_url}/report/{report_id}"
        filename = f"report_qr_{report_id}.png"
        return self.generate_qr(data, filename=filename, fill_color="#1e293b", back_color="#f8fafc")

    # ------------------------------------------
    #  Patient ID QR
    # ------------------------------------------
    def generate_patient_id_qr(self, patient_id: str, patient_name: str = "") -> Dict:
        """Generate a QR code for patient identification."""
        data = f"HOSPITALIQ-PATIENT|ID:{patient_id}|NAME:{patient_name}|DATE:{datetime.utcnow().isoformat()}"
        filename = f"patient_qr_{patient_id}.png"
        return self.generate_qr(data, filename=filename, fill_color="#0f172a", back_color="#ffffff")

    # ------------------------------------------
    #  Appointment QR
    # ------------------------------------------
    def generate_appointment_qr(
        self,
        appointment_id: str,
        patient_name: str,
        doctor_name: str,
        date: str,
        time: str,
    ) -> Dict:
        """Generate a QR code for appointment verification."""
        data = (
            f"HOSPITALIQ-APPT|ID:{appointment_id}"
            f"|PATIENT:{patient_name}|DOCTOR:{doctor_name}"
            f"|DATE:{date}|TIME:{time}"
        )
        filename = f"appt_qr_{appointment_id}.png"
        return self.generate_qr(data, filename=filename, fill_color="#166534", back_color="#f0fdf4")


# ============================================
#  Module-level singleton instances
# ============================================
email_service = EmailService()
tts_service = TTSService()
translation_service = TranslationService()
qr_service = QRCodeService()

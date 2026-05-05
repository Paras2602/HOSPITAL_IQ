"""
============================================
HospitalIQ — Notification Services Test
============================================

Tests TTS, Translation, and QR Code services.
Email test is skipped (no live SMTP credentials in test).

Run:
  python test_notifications.py
"""

import os
import sys

# Ensure project root is on the path so `backend.*` imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils.notifications import (
    tts_service,
    translation_service,
    qr_service,
    email_service,
)


PASS = 0
FAIL = 0


def result(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    status = "✅ PASS" if ok else "❌ FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {status}  {name}" + (f"  ({detail})" if detail else ""))


def divider(title: str):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")


# ============================================
#  1. TTS Tests
# ============================================
def test_tts():
    divider("🔊 TTS — Text-to-Speech")

    # Test basic English TTS
    res = tts_service.text_to_speech(
        text="Hello, welcome to HospitalIQ. Your health report is ready.",
        language="en",
        filename="test_english.mp3",
    )
    ok = res["status"] == "success" and os.path.exists(res.get("filepath", ""))
    result("English TTS generation", ok, res.get("filename", res.get("message", "")))

    # Test Hindi TTS
    res = tts_service.text_to_speech(
        text="नमस्ते, आपका स्वास्थ्य रिपोर्ट तैयार है।",
        language="hi",
        filename="test_hindi.mp3",
    )
    ok = res["status"] == "success" and os.path.exists(res.get("filepath", ""))
    result("Hindi TTS generation", ok, res.get("filename", res.get("message", "")))

    # Test prediction audio
    res = tts_service.generate_prediction_audio(
        disease="Diabetes",
        risk_level="High",
        risk_percentage=78.5,
        recommendations="Reduce sugar intake and exercise regularly.",
        language="en",
    )
    ok = res["status"] == "success" and os.path.exists(res.get("filepath", ""))
    result("Prediction audio generation", ok, res.get("filename", res.get("message", "")))


# ============================================
#  2. Translation Tests
# ============================================
def test_translation():
    divider("🌐 Translation")

    test_text = "Your diabetes risk is high. Please consult your doctor immediately."

    # Hindi
    res = translation_service.translate(test_text, "hi")
    ok = res["status"] == "success" and len(res.get("translated", "")) > 0
    result("English → Hindi", ok, res.get("translated", res.get("message", ""))[:60])

    # Tamil
    res = translation_service.translate(test_text, "ta")
    ok = res["status"] == "success" and len(res.get("translated", "")) > 0
    result("English → Tamil", ok, res.get("translated", res.get("message", ""))[:60])

    # Telugu
    res = translation_service.translate(test_text, "te")
    ok = res["status"] == "success" and len(res.get("translated", "")) > 0
    result("English → Telugu", ok, res.get("translated", res.get("message", ""))[:60])

    # Prediction result translation
    res = translation_service.translate_prediction_result(
        disease="Heart Disease",
        risk_level="Moderate",
        risk_percentage=55.3,
        recommendations="Monitor blood pressure and reduce salt intake.",
        target_language="hi",
    )
    ok = res["status"] == "success"
    result("Prediction result → Hindi", ok, res.get("translated", res.get("message", ""))[:60])

    # Supported languages
    langs = translation_service.get_supported_languages()
    ok = langs["status"] == "success" and langs["count"] > 0
    result("Get supported languages", ok, f"{langs['count']} languages")

    if langs["status"] == "success":
        print("\n  📋 Supported Languages:")
        for code, name in langs["languages"].items():
            print(f"     {code:6s} → {name}")


# ============================================
#  3. QR Code Tests
# ============================================
def test_qr():
    divider("📱 QR Code Generation")

    # Generic QR
    res = qr_service.generate_qr(
        data="https://hospitaliq.com/test",
        filename="test_generic.png",
    )
    ok = res["status"] == "success" and os.path.exists(res.get("filepath", ""))
    result("Generic QR code", ok, res.get("filename", res.get("message", "")))

    # Patient ID QR
    res = qr_service.generate_patient_id_qr(
        patient_id="PAT-2025-001",
        patient_name="John Doe",
    )
    ok = res["status"] == "success" and os.path.exists(res.get("filepath", ""))
    result("Patient ID QR", ok, res.get("filename", res.get("message", "")))

    # Report QR
    res = qr_service.generate_report_qr(report_id="RPT-2025-042")
    ok = res["status"] == "success" and os.path.exists(res.get("filepath", ""))
    result("Report QR", ok, res.get("filename", res.get("message", "")))

    # Appointment QR
    res = qr_service.generate_appointment_qr(
        appointment_id="APT-2025-101",
        patient_name="John Doe",
        doctor_name="Dr. Smith",
        date="2025-07-15",
        time="10:30 AM",
    )
    ok = res["status"] == "success" and os.path.exists(res.get("filepath", ""))
    result("Appointment QR", ok, res.get("filename", res.get("message", "")))


# ============================================
#  4. Email (SKIPPED — no live credentials)
# ============================================
def test_email():
    divider("📧 Email (SKIPPED)")
    print("  ⏭️  Email tests skipped — no SMTP credentials configured")
    print(f"  ℹ️  SMTP Server: {email_service.smtp_server}")
    print(f"  ℹ️  Sender:      {email_service.sender_email}")
    print(f"  ℹ️  Password:    {'***' if email_service.sender_password else '(not set)'}")


# ============================================
#  MAIN
# ============================================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  🏥 HospitalIQ — Notification Services Test")
    print("=" * 50)

    test_tts()
    test_translation()
    test_qr()
    test_email()

    # Summary
    total = PASS + FAIL
    divider("📊 TEST SUMMARY")
    print(f"  Total:  {total}")
    print(f"  Passed: {PASS} ✅")
    print(f"  Failed: {FAIL} ❌")
    print()

    if FAIL == 0:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print(f"  ⚠️  {FAIL} test(s) failed — check output above")

    print()

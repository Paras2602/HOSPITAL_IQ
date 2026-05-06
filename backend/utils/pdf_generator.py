"""PDF report generation with ReportLab + QR code."""
import io, os, json
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PIL import Image as PILImage
import base64
from datetime import datetime


BRAND_BLUE = colors.HexColor("#2563eb")
BRAND_DARK = colors.HexColor("#0f172a")
BRAND_SLATE = colors.HexColor("#475569")
RISK_COLORS = {
    "low": colors.HexColor("#22c55e"),
    "moderate": colors.HexColor("#f59e0b"),
    "high": colors.HexColor("#ef4444"),
}


def generate_pdf_report(
    patient_data: dict,
    prediction_data: dict,
    hospital_name: str = "HospitalIQ",
    report_url: str = "",
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Header
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=22, textColor=BRAND_BLUE, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        fontSize=10, textColor=BRAND_SLATE
    )
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Heading2"],
        fontSize=13, textColor=BRAND_BLUE, spaceBefore=14, spaceAfter=4
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#1e293b"), spaceAfter=4
    )
    disclaimer_style = ParagraphStyle(
        "Disc", parent=styles["Normal"],
        fontSize=8, textColor=BRAND_SLATE, spaceAfter=4
    )

    story.append(Paragraph(f"🏥 {hospital_name}", title_style))
    story.append(Paragraph("AI-Powered Clinical Decision Support Report", sub_style))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceAfter=12))

    # Patient Info
    story.append(Paragraph("Patient Information", heading_style))
    pt = patient_data
    patient_rows = [
        ["Patient ID", pt.get("patient_id", "—"), "Name", pt.get("full_name", "—")],
        ["Age", str(pt.get("age", "—")), "Sex", pt.get("sex", "—")],
        ["Blood Group", pt.get("blood_group", "—"), "BMI", _calc_bmi(pt)],
        ["Chronic Conditions", pt.get("chronic_conditions", "None"), "Allergies", pt.get("allergies", "None")],
    ]
    pt_table = Table(patient_rows, colWidths=[3.5 * cm, 5 * cm, 3.5 * cm, 5 * cm])
    pt_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eff6ff")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(pt_table)
    story.append(Spacer(1, 12))

    # Prediction
    story.append(Paragraph("Prediction Results", heading_style))
    from backend.utils.clinical import format_disease_name
    disease = format_disease_name(prediction_data.get("disease", "Unknown"))
    risk_pct = prediction_data.get("risk_percent", 0)
    risk_label = prediction_data.get("risk_label", "unknown")
    risk_color = RISK_COLORS.get(risk_label, colors.gray)

    pred_rows = [
        ["Disease", disease],
        ["Risk Probability", f"{risk_pct:.1f}%"],
        ["Risk Level", risk_label.upper()],
        ["Model Version", prediction_data.get("model_version", "v1.0")],
    ]
    pred_table = Table(pred_rows, colWidths=[5 * cm, 12 * cm])
    pred_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (1, 2), (1, 2), risk_color),
    ]))
    story.append(pred_table)
    story.append(Spacer(1, 12))

    # SHAP Chart
    shap_b64 = prediction_data.get("shap_plot_base64")
    if shap_b64:
        try:
            story.append(Paragraph("SHAP Feature Importance", heading_style))
            img_data = base64.b64decode(shap_b64)
            img_buf = io.BytesIO(img_data)
            pil_img = PILImage.open(img_buf)
            tmp_path = "/tmp/shap_plot.png"
            pil_img.save(tmp_path)
            img = RLImage(tmp_path, width=14 * cm, height=6 * cm)
            story.append(img)
            story.append(Spacer(1, 8))
        except Exception:
            pass

    # SHAP values table
    shap_vals = prediction_data.get("shap_values", {})
    if shap_vals:
        sorted_shap = sorted(shap_vals.items(), key=lambda x: abs(x[1]), reverse=True)[:6]
        story.append(Paragraph("Top Contributing Features (SHAP)", heading_style))
        shap_rows = [["Feature", "SHAP Value", "Direction"]] + [
            [k, f"{v:.4f}", "↑ Risk" if v > 0 else "↓ Risk"]
            for k, v in sorted_shap
        ]
        shap_table = Table(shap_rows, colWidths=[6 * cm, 4 * cm, 7 * cm])
        shap_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(shap_table)
        story.append(Spacer(1, 12))

    # Recommendations
    recs = prediction_data.get("recommendations", "")
    if recs:
        story.append(Paragraph("Clinical Recommendations", heading_style))
        story.append(Paragraph(recs, body_style))
        story.append(Spacer(1, 12))

    # QR Code
    if report_url:
        story.append(Paragraph("Verify Report Online", heading_style))
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(report_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format="PNG")
        qr_buf.seek(0)
        qr_rl = RLImage(qr_buf, width=3 * cm, height=3 * cm)
        story.append(qr_rl)
        story.append(Paragraph(f"URL: {report_url}", disclaimer_style))
        story.append(Spacer(1, 12))

    # Disclaimer
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_SLATE, spaceAfter=6))
    story.append(Paragraph(
        "⚠️ DISCLAIMER: HospitalIQ is a clinical decision SUPPORT tool only. "
        "This report must not be used as a standalone diagnosis. "
        "Final clinical decisions must be made by licensed healthcare professionals.",
        disclaimer_style,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def _calc_bmi(pt: dict) -> str:
    h = pt.get("height_cm")
    w = pt.get("weight_kg")
    if h and w and h > 0:
        bmi = w / ((h / 100) ** 2)
        return f"{bmi:.1f}"
    return "—"

def generate_prescription_pdf(
    prescription_data: dict,
    hospital_name: str = "HospitalIQ",
    hospital_address: str = "123 Healthcare Blvd, Medical City, MC 10101",
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Custom Styles
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=22, textColor=BRAND_BLUE, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        fontSize=10, textColor=BRAND_SLATE
    )
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Heading2"],
        fontSize=13, textColor=BRAND_BLUE, spaceBefore=14, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=BRAND_DARK, leading=14
    )
    warning_style = ParagraphStyle(
        "Warning", parent=styles["Normal"],
        fontSize=11, textColor=colors.white, alignment=TA_CENTER,
        leading=14, fontName="Helvetica-Bold"
    )

    # Header
    story.append(Paragraph(f"🏥 {hospital_name}", title_style))
    story.append(Paragraph("Official Clinical Prescription", sub_style))
    story.append(Paragraph(f"Date: {datetime.utcnow().strftime('%d %B %Y')}", sub_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_BLUE, spaceAfter=12))

    # Patient & Doctor Info Header
    p_info = prescription_data.get("patient", {})
    d_info = prescription_data.get("doctor", {})
    
    info_rows = [
        [Paragraph(f"<b>PATIENT:</b> {p_info.get('name', '—')}", body_style), 
         Paragraph(f"<b>DOCTOR:</b> {d_info.get('name', '—')}", body_style)],
        [Paragraph(f"<b>Age/Sex:</b> {p_info.get('age', '—')} / {p_info.get('sex', '—')}", body_style),
         Paragraph(f"<b>Reg No:</b> {d_info.get('registration_number', '—')}", body_style)],
        [Paragraph(f"<b>Patient ID:</b> {p_info.get('id', '—')}", body_style),
         Paragraph(f"<b>Qualification:</b> {d_info.get('qualification', '—')}", body_style)]
    ]
    info_table = Table(info_rows, colWidths=[9 * cm, 8 * cm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_SLATE, spaceAfter=12))

    # Diagnosis Section
    from backend.utils.clinical import format_disease_name
    formatted_disease = format_disease_name(prescription_data.get("disease", "Unknown"))
    
    story.append(Paragraph("Diagnosis", heading_style))
    story.append(Paragraph(f"<b>Primary:</b> {formatted_disease}", body_style))
    story.append(Paragraph(f"<b>Severity:</b> {prescription_data.get('severity', 'Moderate')}", body_style))
    
    # Emergency Warning Box
    if str(prescription_data.get("severity", "")).lower() in ["severe", "critical"]:
        story.append(Spacer(1, 10))
        warning_data = [[Paragraph("URGENT: This patient requires immediate medical attention.<br/>Please schedule an in-person consultation within 24 hours.", warning_style)]]
        warning_table = Table(warning_data, colWidths=[16 * cm])
        warning_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ef4444")),
            ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#991b1b")),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(warning_table)
        story.append(Spacer(1, 10))

    # Medicines
    story.append(Paragraph("Prescribed Medications", heading_style))
    meds = prescription_data.get("medicines", [])
    if meds:
        med_rows = [["#", "Medicine", "Dosage", "Frequency", "Duration"]]
        for i, m in enumerate(meds, 1):
            med_rows.append([
                str(i),
                Paragraph(f"<b>{m.get('name', '—')}</b>", body_style),
                m.get("dosage", "—"),
                m.get("frequency", "—"),
                m.get("duration", "—")
            ])
        
        med_table = Table(med_rows, colWidths=[1 * cm, 6 * cm, 3 * cm, 4 * cm, 3 * cm])
        med_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_DARK),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(med_table)
    else:
        story.append(Paragraph("No medications prescribed.", body_style))

    # Advice Section
    story.append(Paragraph("Clinical Advice & Precautions", heading_style))
    precautions = prescription_data.get("precautions", "")
    if precautions:
        story.append(Paragraph("<b>Precautions:</b>", body_style))
        for p in precautions.split("\n"):
            if p.strip():
                story.append(Paragraph(f"• {p.strip().lstrip('- ')}", body_style))
    
    diet = prescription_data.get("dietary_advice", "")
    if diet:
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Dietary Advice:</b>", body_style))
        story.append(Paragraph(diet, body_style))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_SLATE, spaceAfter=20))

    # Footer / Signature
    footer_rows = [
        [
            Paragraph(f"<b>HospitalIQ Clinical Center</b><br/>{hospital_address}<br/>Contact: {d_info.get('contact', 'Support')}", sub_style),
            Paragraph("<br/><b>[Digitally Verified]</b><br/>Dr. " + d_info.get('name', 'Unknown'), ParagraphStyle("Sig", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10))
        ]
    ]
    footer_table = Table(footer_rows, colWidths=[10 * cm, 7 * cm])
    story.append(footer_table)

    doc.build(story)
    buf.seek(0)
    return buf.read()

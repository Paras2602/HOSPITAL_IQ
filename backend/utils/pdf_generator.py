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
    disease = prediction_data.get("disease", "Unknown").title()
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
    prescription_text: str,
    hospital_name: str = "HospitalIQ",
    prescription_id: str = "",
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

    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=22, textColor=BRAND_BLUE, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        fontSize=10, textColor=BRAND_SLATE
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#1e293b"), spaceAfter=4,
        fontName="Courier" # use monospace for the text block
    )

    story.append(Paragraph(f"🏥 {hospital_name}", title_style))
    story.append(Paragraph("Clinical Prescription", sub_style))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceAfter=12))

    # Convert the formatted text to a simple pre-formatted style
    for line in prescription_text.split('\n'):
        # Replacing spaces with non-breaking spaces for Courier to maintain alignment
        formatted_line = line.replace(' ', '&nbsp;')
        story.append(Paragraph(formatted_line, body_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 12))
    
    # QR Code
    story.append(Paragraph("Verify Prescription Online", ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=13, textColor=BRAND_BLUE)))
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(f"https://hospitaliq.com/verify/{prescription_id}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_rl = RLImage(qr_buf, width=3 * cm, height=3 * cm)
    story.append(qr_rl)

    doc.build(story)
    buf.seek(0)
    return buf.read()

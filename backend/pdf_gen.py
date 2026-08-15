"""Generate the FTECH04R5-style Calibration Certificate PDF (reproduces the
existing Excel certificate layout) with an embedded QR verification code."""
import io
from datetime import datetime
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)

NAVY = colors.HexColor("#0F172A")
BLUE = colors.HexColor("#2563EB")
GREY = colors.HexColor("#E2E8F0")
LIGHT = colors.HexColor("#F1F5F9")


def _fmt_date(v):
    if not v:
        return ""
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v.replace("Z", "")[:19])
        except Exception:
            return v
    return v.strftime("%d-%m-%Y")


def _qr_image(url):
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def build_certificate_pdf(job, customer, product, results, verify_url):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=7.5, leading=9.5)
    smallb = ParagraphStyle("smallb", parent=small, fontName="Helvetica-Bold")
    title = ParagraphStyle("title", parent=styles["Title"], fontSize=15, textColor=NAVY, spaceAfter=2)
    story = []

    story.append(Paragraph("YOG ELECTRO PROCESS PVT. LTD.", ParagraphStyle(
        "co", parent=styles["Title"], fontSize=13, textColor=BLUE, spaceAfter=0)))
    story.append(Paragraph("(Calibration Laboratory)", ParagraphStyle(
        "co2", parent=styles["Normal"], fontSize=8, alignment=1, textColor=colors.grey)))
    story.append(Spacer(1, 4))
    story.append(Paragraph("CALIBRATION CERTIFICATE", title))
    story.append(Spacer(1, 2))

    meta = [
        [Paragraph("<b>Certificate No.:</b> " + str(job.get("cert_no", "")), small),
         Paragraph("<b>Calibration Date:</b> " + _fmt_date(job.get("cal_date")), small)],
        [Paragraph("<b>ULR No.:</b> " + str(job.get("ulr_no", "")), small),
         Paragraph("<b>Issue Date:</b> " + _fmt_date(job.get("issue_date")), small)],
        [Paragraph("<b>Job No.:</b> " + str(job.get("job_no", "")), small),
         Paragraph("<b>Item Received Date:</b> " + _fmt_date(job.get("item_received_date")), small)],
        [Paragraph("<b>Item Condition on receipt:</b> OK", small),
         Paragraph("<b>Recommended Next Calibration:</b> " + _fmt_date(job.get("recommended_next_date")), small)],
    ]
    mt = Table(meta, colWidths=[92 * mm, 90 * mm])
    mt.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, NAVY),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(mt)
    story.append(Spacer(1, 4))

    def section(txt):
        story.append(Paragraph(txt, smallb))

    section("1. Calibrated For (Name & Address):")
    story.append(Paragraph(f"{customer.get('name','')}<br/>{customer.get('address','')}", small))
    section("2. Calibration Location: Calibration Lab &nbsp;&nbsp; 3. Condition of Item on received: OK")
    section("4. Description of Item (UUC):")
    desc = [[
        Paragraph(f"<b>Name:</b> {product.get('name','')}", small),
        Paragraph(f"<b>Make:</b> {product.get('make','')}", small),
    ], [
        Paragraph(f"<b>Sr. No.:</b> {job.get('serial_number','')}", small),
        Paragraph(f"<b>Range:</b> {product.get('range','')}", small),
    ], [
        Paragraph(f"<b>Type:</b> {product.get('type','')}", small),
        Paragraph(f"<b>Tag No.:</b> {job.get('tag_number','') or '-'}", small),
    ]]
    dt = Table(desc, colWidths=[110 * mm, 72 * mm])
    dt.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, GREY),
                            ("INNERGRID", (0, 0), (-1, -1), 0.3, GREY),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    story.append(dt)
    story.append(Spacer(1, 4))

    section("5. Calibration Standards Used:")
    std_head = ["Sr", "Name", "Unc of Std (±°C)", "ID/Sr. No.", "Certified By", "Report No.", "Validity"]
    std_rows = [std_head]
    for i, s in enumerate(job.get("standards_used", []), 1):
        std_rows.append([str(i), s.get("name", ""), str(s.get("uncertainty", "")),
                         s.get("id_no", ""), s.get("certified_by", ""),
                         s.get("report_no", ""), _fmt_date(s.get("validity"))])
    stbl = Table(std_rows, colWidths=[8 * mm, 46 * mm, 22 * mm, 30 * mm, 24 * mm, 30 * mm, 22 * mm])
    stbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(stbl)
    story.append(Spacer(1, 4))

    section(f"6. Method Used: {job.get('method','')} &nbsp; (Ref. standard: {job.get('reference_standard','')})")
    env = job.get("environmental", {})
    section(f"7. Environmental Conditions: Humidity: {env.get('humidity','')} &nbsp;&nbsp; Ambient Temperature: {env.get('ambient_temp','')}")
    section("8. Calibration Results:")
    res_head = ["Sr", "Standard Value (°C)", "Measured Value on UUC (°C)", "Deviation (°C)", "Expanded Uncertainty (±°C)"]
    res_rows = [res_head]
    for i, p in enumerate(results, 1):
        r = p["results"]
        res_rows.append([str(i), f"{r['corrected_std']:.2f}", f"{r['uut_mean']:.2f}",
                         f"{r['deviation']:.2f}", f"{r['reported_uncertainty']:.2f}"])
    rtbl = Table(res_rows, colWidths=[10 * mm, 42 * mm, 52 * mm, 34 * mm, 44 * mm])
    rtbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Courier"),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(rtbl)
    story.append(Paragraph("UUC: Unit under Calibration", ParagraphStyle("n", parent=small, fontSize=6.5, textColor=colors.grey)))
    story.append(Spacer(1, 4))

    section("9. Remarks:")
    remarks = [
        "A Sticker indicating \u201cCALIBRATION STATUS\u201d has been affixed on the UUC.",
        "The standards used for calibration were calibrated using reference standard traceable to National / International Standard.",
        "The reported expanded UNCERTAINTY is calculated at 95.45 % confidence level where coverage factor k=2.",
        "Calibration Points were selected as per customer\u2019s specifications.",
        "The calibration results reported in this certificate are related to this item only and valid at the time of and under stated conditions of measurement.",
        "This certificate shall not be reproduced except in full, without written permission of the laboratory.",
        "Unless otherwise specified, results are applicable only to the calibrated product.",
        "Above calibration done is meant for scientific & industrial purpose only.",
    ]
    for i, rm in enumerate(remarks, 1):
        story.append(Paragraph(f"{i}. {rm}", ParagraphStyle("rm", parent=small, fontSize=6.8, leading=8.5)))
    story.append(Spacer(1, 6))

    qr_img = Image(_qr_image(verify_url), width=22 * mm, height=22 * mm)
    sign = [[
        Paragraph("<b>Calibrated By:</b><br/><br/>Mr. N. H. Bodakhe<br/>(Calibration Engineer)", small),
        Paragraph("<b>Approved By:</b><br/><br/>Mr. A. A. Kothe<br/>(Technical Manager)", small),
        qr_img,
    ]]
    st = Table(sign, colWidths=[75 * mm, 75 * mm, 32 * mm])
    st.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("ALIGN", (2, 0), (2, 0), "CENTER"),
                            ("BOX", (0, 0), (-1, -1), 0.5, GREY)]))
    story.append(st)
    story.append(Paragraph(f"Scan QR to verify \u2022 {verify_url}", ParagraphStyle("v", parent=small, fontSize=6.5, alignment=1, textColor=colors.grey)))
    story.append(Paragraph("(---- End of the Certificate ----)", ParagraphStyle("end", parent=small, alignment=1, fontSize=7)))

    doc.build(story)
    buf.seek(0)
    return buf

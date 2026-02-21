from io import BytesIO

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _wrap_text(c, text, max_width, font_name, font_size):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if c.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_cover_pdf(
    trim_size,
    page_count,
    bleed_in,
    spine_in,
    safe_in,
    title,
    subtitle,
    author,
    back_text,
):
    trim_w, trim_h = trim_size
    cover_w = (2 * trim_w + spine_in + 2 * bleed_in) * inch
    cover_h = (trim_h + 2 * bleed_in) * inch

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(cover_w, cover_h))

    bleed_pt = bleed_in * inch
    spine_pt = spine_in * inch
    safe_pt = safe_in * inch

    back_left = bleed_pt
    back_right = bleed_pt + trim_w * inch
    spine_left = back_right
    spine_right = spine_left + spine_pt
    front_left = spine_right
    front_right = front_left + trim_w * inch

    c.setStrokeColorRGB(0.6, 0.6, 0.6)
    c.setLineWidth(0.5)
    c.rect(bleed_pt, bleed_pt, trim_w * inch, trim_h * inch)
    c.rect(front_left, bleed_pt, trim_w * inch, trim_h * inch)

    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    c.line(spine_left, bleed_pt, spine_left, cover_h - bleed_pt)
    c.line(spine_right, bleed_pt, spine_right, cover_h - bleed_pt)

    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.rect(
        back_left + safe_pt,
        bleed_pt + safe_pt,
        trim_w * inch - 2 * safe_pt,
        trim_h * inch - 2 * safe_pt,
    )
    c.rect(
        front_left + safe_pt,
        bleed_pt + safe_pt,
        trim_w * inch - 2 * safe_pt,
        trim_h * inch - 2 * safe_pt,
    )

    c.setFillColorRGB(0, 0, 0)
    title_font = 32
    subtitle_font = 16
    author_font = 14

    front_center_x = (front_left + front_right) / 2
    front_center_y = bleed_pt + (trim_h * inch) / 2
    c.setFont("Helvetica-Bold", title_font)
    c.drawCentredString(front_center_x, front_center_y + 60, title)
    if subtitle:
        c.setFont("Helvetica", subtitle_font)
        c.drawCentredString(front_center_x, front_center_y + 30, subtitle)
    c.setFont("Helvetica", author_font)
    c.drawCentredString(front_center_x, bleed_pt + safe_pt + 30, author)

    c.setFont("Helvetica", 12)
    back_text_width = trim_w * inch - 2 * safe_pt
    lines = _wrap_text(c, back_text, back_text_width, "Helvetica", 12)
    start_y = bleed_pt + trim_h * inch - safe_pt - 40
    line_height = 14
    for line in lines:
        if start_y < bleed_pt + safe_pt + 40:
            break
        c.drawString(back_left + safe_pt, start_y, line)
        start_y -= line_height

    if spine_in > 0:
        c.saveState()
        spine_center_x = (spine_left + spine_right) / 2
        spine_center_y = cover_h / 2
        c.translate(spine_center_x, spine_center_y)
        c.rotate(90)
        c.setFont("Helvetica-Bold", 14)
        spine_text = title if len(title) <= 40 else title[:40]
        c.drawCentredString(0, -5, spine_text)
        c.restoreState()

    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(back_left + 6, bleed_pt + 6, f"Page count: {page_count}")

    c.save()
    buffer.seek(0)
    return buffer

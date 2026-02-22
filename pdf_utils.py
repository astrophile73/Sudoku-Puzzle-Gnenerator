from io import BytesIO

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _draw_grid(c, grid, x, y, size_pt, spec, show_all=False):
    n = spec.size
    cell = size_pt / n

    for i in range(n + 1):
        line_w = 1.6 if i % spec.block_rows == 0 else 0.6
        c.setLineWidth(line_w)
        y_pos = y + i * cell
        c.line(x, y_pos, x + size_pt, y_pos)

    for i in range(n + 1):
        line_w = 1.6 if i % spec.block_cols == 0 else 0.6
        c.setLineWidth(line_w)
        x_pos = x + i * cell
        c.line(x_pos, y, x_pos, y + size_pt)

    max_digits = len(str(n))
    base_size = max(6, cell * 0.55)
    if max_digits >= 2:
        base_size *= 0.85
    font_name = "Helvetica" if show_all else "Helvetica-Bold"
    c.setFont(font_name, base_size)

    for r in range(n):
        for c_idx in range(n):
            val = grid[r][c_idx]
            if val == 0:
                continue
            tx = x + c_idx * cell + cell / 2
            ty = y + (n - 1 - r) * cell + cell / 2
            c.drawCentredString(tx, ty - base_size * 0.35, str(val))


def _draw_page(
    c,
    items,
    spec,
    page_size,
    margin_pt,
    layout,
    start_index,
    show_all=False,
    title=None,
    include_page_numbers=False,
    page_number=None,
    item_label="Puzzle",
):
    page_w, page_h = page_size
    rows, cols = layout

    title_h = 0
    if title:
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(page_w / 2, page_h - margin_pt * 0.6, title)
        title_h = 24

    avail_w = page_w - 2 * margin_pt
    avail_h = page_h - 2 * margin_pt - title_h
    cell_w = avail_w / cols
    cell_h = avail_h / rows
    grid_size = max(24, min(cell_w, cell_h) - 10)

    for idx, grid in enumerate(items):
        r = idx // cols
        c_idx = idx % cols
        left = margin_pt + c_idx * cell_w + (cell_w - grid_size) / 2
        bottom = margin_pt + (rows - 1 - r) * cell_h + (cell_h - grid_size) / 2
        puzzle_number = start_index + idx + 1
        label_y = bottom + grid_size + 6
        if label_y < page_h - margin_pt:
            c.setFont("Helvetica", 9)
            c.drawString(left, label_y, f"{item_label} {puzzle_number}")
        _draw_grid(c, grid, left, bottom, grid_size, spec, show_all=show_all)

    if include_page_numbers and page_number is not None:
        c.setFont("Helvetica", 9)
        c.drawCentredString(page_w / 2, margin_pt * 0.4, str(page_number))


def build_interior_pdf(
    puzzle_sections,
    solution_sections,
    trim_size,
    margin_in,
    include_page_numbers=True,
):
    page_w = trim_size[0] * inch
    page_h = trim_size[1] * inch
    margin_pt = margin_in * inch

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))

    page_num = 1
    for section in puzzle_sections:
        items = section["items"]
        spec = section["spec"]
        layout = section["layout"]
        start_index = section["start_index"]
        per_page = layout[0] * layout[1]
        for start in range(0, len(items), per_page):
            page_items = items[start : start + per_page]
            page_title = section["title"] if start == 0 else None
            _draw_page(
                c,
                page_items,
                spec,
                (page_w, page_h),
                margin_pt,
                layout,
                start_index=start_index + start,
                show_all=False,
                title=page_title,
                include_page_numbers=include_page_numbers,
                page_number=page_num,
                item_label="Puzzle",
            )
            c.showPage()
            page_num += 1

    for section in solution_sections:
        items = section["items"]
        spec = section["spec"]
        layout = section["layout"]
        start_index = section["start_index"]
        per_page = layout[0] * layout[1]
        for start in range(0, len(items), per_page):
            page_items = items[start : start + per_page]
            page_title = section["title"] if start == 0 else None
            _draw_page(
                c,
                page_items,
                spec,
                (page_w, page_h),
                margin_pt,
                layout,
                start_index=start_index + start,
                show_all=True,
                title=page_title,
                include_page_numbers=include_page_numbers,
                page_number=page_num,
                item_label="Solution",
            )
            c.showPage()
            page_num += 1

    c.save()
    buffer.seek(0)
    return buffer

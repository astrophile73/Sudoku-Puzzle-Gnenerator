from io import BytesIO

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from fonts import FONT_BOLD, FONT_REG, ensure_fonts_registered


MIN_FONT_PT = 7.0
MIN_LINE_PT = 0.75


def _draw_grid(c, grid, x, y, size_pt, spec, show_all=False):
    n = spec.size
    cell = size_pt / n

    for i in range(n + 1):
        line_w = max(MIN_LINE_PT, 1.5 if i % spec.block_rows == 0 else MIN_LINE_PT)
        c.setLineWidth(line_w)
        y_pos = y + i * cell
        c.line(x, y_pos, x + size_pt, y_pos)

    for i in range(n + 1):
        line_w = max(MIN_LINE_PT, 1.5 if i % spec.block_cols == 0 else MIN_LINE_PT)
        c.setLineWidth(line_w)
        x_pos = x + i * cell
        c.line(x_pos, y, x_pos, y + size_pt)

    max_digits = len(str(n))
    base_size = max(MIN_FONT_PT, cell * 0.55)
    if max_digits >= 2:
        base_size *= 0.85
    font_name = FONT_REG if show_all else FONT_BOLD
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
    inside_margin_pt,
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

    # Facing pages: odd pages are right-hand (inside margin on left),
    # even pages are left-hand (inside margin on right).
    if page_number is None:
        page_number = 1
    if page_number % 2 == 1:
        left_margin = inside_margin_pt
        right_margin = margin_pt
    else:
        left_margin = margin_pt
        right_margin = inside_margin_pt

    content_x0 = left_margin
    content_y0 = margin_pt
    content_x1 = page_w - right_margin
    content_y1 = page_h - margin_pt

    header_h = 0
    if title:
        header_h = 20
    footer_h = 14 if include_page_numbers else 0

    # Header inside content rect.
    if title:
        c.setFont(FONT_BOLD, 14)
        c.drawCentredString((content_x0 + content_x1) / 2, content_y1 - 14, title)

    # Footer inside content rect.
    if include_page_numbers and page_number is not None:
        c.setFont(FONT_REG, 9)
        c.drawCentredString((content_x0 + content_x1) / 2, content_y0 + 2, str(page_number))

    avail_w = content_x1 - content_x0
    avail_h = (content_y1 - content_y0) - header_h - footer_h
    cell_w = avail_w / cols
    cell_h = avail_h / rows
    label_font = 8
    label_h = label_font + 3
    padding = 6
    grid_size = min(cell_w, cell_h - label_h) - padding
    if grid_size < 0:
        grid_size = 0

    for idx, grid in enumerate(items):
        r = idx // cols
        c_idx = idx % cols
        cell_left = content_x0 + c_idx * cell_w
        cell_bottom = content_y0 + footer_h + (rows - 1 - r) * cell_h
        cell_top = cell_bottom + cell_h

        # Label inside cell (top-left), and grid below it.
        label_y = cell_top - label_font - 1
        puzzle_number = start_index + idx + 1
        c.setFont(FONT_REG, label_font)
        label = f"{item_label[0]}{puzzle_number}"
        c.drawString(cell_left + 2, label_y, label)

        if grid_size > 0:
            grid_left = cell_left + (cell_w - grid_size) / 2
            grid_bottom = cell_bottom + 2
            _draw_grid(c, grid, grid_left, grid_bottom, grid_size, spec, show_all=show_all)


def build_interior_pdf(
    puzzle_sections,
    solution_sections,
    trim_size,
    margin_in,
    inside_margin_in,
    include_page_numbers=True,
    force_even_pages=True,
):
    ensure_fonts_registered()
    page_w = trim_size[0] * inch
    page_h = trim_size[1] * inch
    margin_pt = margin_in * inch
    inside_margin_pt = inside_margin_in * inch

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
                inside_margin_pt,
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
                inside_margin_pt,
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

    total_drawn = page_num - 1
    if force_even_pages and total_drawn % 2 == 1:
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer

import math
import random
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import streamlit as st

from cover import build_cover_pdf
from pdf_utils import build_interior_pdf
from sudoku import generate_puzzles, spec_for_size
from kdp_specs import (
    KDP_MIN_OUTSIDE_TOP_BOTTOM_IN,
    build_margin_spec_no_bleed,
    compute_even_page_count,
    required_inside_margin_no_bleed,
    validate_page_count,
)
from fonts import ensure_fonts_registered


TRIM_SIZES = [
    ("5 x 8 in", (5.0, 8.0)),
    ("5.06 x 7.81 in", (5.06, 7.81)),
    ("5.25 x 8 in", (5.25, 8.0)),
    ("5.5 x 8.5 in", (5.5, 8.5)),
    ("6 x 9 in", (6.0, 9.0)),
    ("6.14 x 9.21 in", (6.14, 9.21)),
    ("6.69 x 9.61 in", (6.69, 9.61)),
    ("7 x 10 in", (7.0, 10.0)),
    ("7.44 x 9.69 in", (7.44, 9.69)),
    ("7.5 x 9.25 in", (7.5, 9.25)),
    ("8 x 10 in", (8.0, 10.0)),
    ("8.25 x 6 in", (8.25, 6.0)),
    ("8.25 x 8.25 in", (8.25, 8.25)),
    ("8.5 x 8.5 in", (8.5, 8.5)),
    ("8.5 x 11 in", (8.5, 11.0)),
    ("8.27 x 11.69 in", (8.27, 11.69)),
]

SIZES = [6, 9, 16]
DIFFICULTIES = ["Easy", "Medium", "Hard", "Expert"]


def _layout_from_per_page(per_page):
    per_page = max(1, int(per_page))
    rows = max(1, int(math.floor(math.sqrt(per_page))))
    cols = int(math.ceil(per_page / rows))
    return rows, cols


def _pages_needed(puzzle_count, rows, cols):
    per_page = max(1, rows * cols)
    return int(math.ceil(puzzle_count / per_page))


st.set_page_config(page_title="Sudoku Book Generator", layout="wide")
st.title("Sudoku Book Generator for Amazon KDP")

with st.sidebar:
    st.header("Puzzle Settings")
    seed_text = st.text_input("Random seed (optional)", value="")

    st.header("Puzzle Mix")
    counts = {size: {} for size in SIZES}
    per_page_by_size = {}
    for size in SIZES:
        with st.expander(f"{size}x{size} settings", expanded=(size == 9)):
            per_page_default = 1 if size == 16 else 4
            per_page = st.number_input(
                "Puzzles per page",
                min_value=1,
                max_value=36,
                value=per_page_default,
                step=1,
                key=f"per_page_{size}",
            )
            per_page_by_size[size] = int(per_page)
            for difficulty in DIFFICULTIES:
                default_count = 10 if (size == 9 and difficulty == "Easy") else 0
                count = st.number_input(
                    f"{difficulty} puzzles",
                    min_value=0,
                    max_value=2000,
                    value=default_count,
                    step=5,
                    key=f"count_{size}_{difficulty}",
                )
                counts[size][difficulty] = int(count)

    st.header("Book Size")
    trim_label = st.selectbox("Trim size (KDP presets)", [label for label, _ in TRIM_SIZES], index=4)
    trim_w, trim_h = dict(TRIM_SIZES)[trim_label]
    margin_in = st.number_input(
        "Outside/Top/Bottom margin (in)",
        min_value=KDP_MIN_OUTSIDE_TOP_BOTTOM_IN,
        max_value=1.5,
        value=0.5,
        step=0.05,
        help="KDP minimum is 0.25 in. Inside (gutter) is computed from page count.",
    )
    extra_gutter_in = st.number_input(
        "Extra gutter (inside) (in)",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.05,
        help="Added on top of the KDP-required inside margin.",
    )
    include_page_numbers = st.checkbox("Include page numbers", value=True)

    st.header("Cover")
    include_cover = st.checkbox("Generate cover PDF", value=True)
    cover_title = st.text_input("Title", value="Sudoku Puzzle Book")
    cover_subtitle = st.text_input("Subtitle", value="Brain-Teasing Puzzles")
    cover_author = st.text_input("Author", value="Your Name")
    cover_back_text = st.text_area(
        "Back cover text",
        value=(
            "Enjoy hours of entertainment with a curated set of Sudoku puzzles. "
            "Perfect for travel, relaxation, and daily brain training."
        ),
        height=120,
    )
    bleed_in = st.number_input("Bleed (in)", min_value=0.0, max_value=0.25, value=0.125, step=0.01)
    spine_in = st.number_input(
        "Spine width (in)",
        min_value=0.0,
        max_value=2.0,
        value=0.5,
        step=0.01,
        help="KDP spine formulas vary by paper type. Enter the spine width you want.",
    )
    safe_in = st.number_input("Safe margin (in)", min_value=0.1, max_value=0.5, value=0.25, step=0.01)

sections = []
total_puzzles = 0
puzzle_pages = 0
for size in SIZES:
    rows, cols = _layout_from_per_page(per_page_by_size[size])
    for difficulty in DIFFICULTIES:
        count = counts[size][difficulty]
        if count <= 0:
            continue
        puzzle_pages += _pages_needed(count, rows, cols)
        total_puzzles += count
        sections.append((size, difficulty, count, rows, cols))

solution_pages = puzzle_pages
raw_total_pages = puzzle_pages + solution_pages
total_pages_even = compute_even_page_count(raw_total_pages)
required_inside = required_inside_margin_no_bleed(total_pages_even)
margins = build_margin_spec_no_bleed(
    page_count_even=total_pages_even,
    outside_top_bottom_in=margin_in,
    extra_gutter_in=extra_gutter_in,
)

st.write(
    "Configure your book and generate a print-ready interior PDF with puzzles and solutions. "
    "Optionally generate a KDP-sized cover PDF."
)
st.info(
    f"Total puzzles: {total_puzzles} | Estimated interior pages: {raw_total_pages} "
    f"(rounded to {total_pages_even} for print)"
)

preflight_errors = []
preflight_warnings = []

# Fonts must be embeddable for KDP.
try:
    font_label = ensure_fonts_registered()
    preflight_warnings.append(f"Using embedded fonts: {font_label}")
except Exception as exc:
    preflight_errors.append(f"Fonts: {exc}")

preflight_errors.extend(validate_page_count(total_pages_even))

# Margin checks (no-bleed).
if margins.outside_in < KDP_MIN_OUTSIDE_TOP_BOTTOM_IN:
    preflight_errors.append("Outside/Top/Bottom margin is below 0.25 in.")
if margins.inside_in < required_inside:
    preflight_errors.append("Inside (gutter) margin is below the KDP requirement.")

# Layout fit checks (conservative): ensure grids + minimum font can fit inside the content rect.
page_w_pt = trim_w * 72.0
page_h_pt = trim_h * 72.0
outside_pt = margins.outside_in * 72.0
inside_pt = margins.inside_in * 72.0
avail_w = page_w_pt - outside_pt - inside_pt
avail_h_total = page_h_pt - margins.top_in * 72.0 - margins.bottom_in * 72.0
header_h = 20.0
footer_h = 14.0 if include_page_numbers else 0.0
label_h = 11.0
padding = 6.0

if avail_w <= 0 or avail_h_total <= 0:
    preflight_errors.append("Margins are too large for this trim size.")
else:
    for size, difficulty, count, rows, cols in sections:
        # Each section has a title on its first page, so we preflight with header reserved.
        avail_h = avail_h_total - header_h - footer_h
        cell_w = avail_w / cols
        cell_h = avail_h / rows
        grid_size = min(cell_w, cell_h - label_h) - padding
        if grid_size <= 0:
            preflight_errors.append(
                f"{size}x{size} {difficulty}: layout {rows}x{cols} does not fit. Reduce puzzles-per-page or use a larger trim size."
            )
            continue
        cell = grid_size / size
        # Digit font is ~0.55*cell, and 16x16 uses a 0.85 scale.
        scale = 0.55 * (0.85 if size >= 10 else 1.0)
        if cell * scale < 7.0:
            preflight_errors.append(
                f"{size}x{size} {difficulty}: cells are too small for 7pt minimum. Reduce puzzles-per-page or increase trim size."
            )

if preflight_errors:
    st.error("KDP Preflight: FAIL")
    for msg in preflight_errors:
        st.write(f"- {msg}")
else:
    st.success("KDP Preflight: PASS")
    for msg in preflight_warnings:
        st.caption(msg)

generate = st.button("Generate PDFs", type="primary", disabled=bool(preflight_errors))

if generate:
    if total_puzzles == 0:
        st.error("Please add at least one puzzle count to generate a book.")
        st.stop()

    rng = random.Random(seed_text) if seed_text else random.Random()

    progress = st.progress(0)
    status = st.empty()
    warnings = []

    def _progress_cb(done, total, detail=None):
        progress.progress(min(1.0, done / max(1, total)))
        if detail:
            status.write(f"{detail} | Overall {done}/{total}")
        else:
            status.write(f"Generating puzzles {done}/{total}...")

    def _warn_cb(index, target, actual):
        warnings.append((index, target, actual))

    with st.spinner("Building puzzles and PDFs..."):
        puzzle_sections = []
        solution_sections = []
        progress_state = {"done": 0}
        start_index = 0

        for size, difficulty, count, rows, cols in sections:
            section_label = f"{size}x{size} {difficulty}"
            spec = spec_for_size(size)
            section_state = {"done": 0}

            def _section_progress_cb(done, total, _label=section_label):
                progress_state["done"] += done - section_state["done"]
                section_state["done"] = done
                _progress_cb(
                    progress_state["done"],
                    total_puzzles,
                    detail=f"Generating {_label}: {done}/{count}",
                )

            def _section_warn_cb(index, target, actual, reason=None, _label=section_label):
                warnings.append((_label, index, target, actual, reason))

            puzzles, solutions = generate_puzzles(
                count=count,
                spec=spec,
                difficulty=difficulty,
                rng=rng,
                progress_cb=_section_progress_cb,
                warn_cb=_section_warn_cb,
            )

            puzzle_sections.append(
                {
                    "title": section_label,
                    "spec": spec,
                    "layout": (rows, cols),
                    "items": puzzles,
                    "start_index": start_index,
                }
            )
            solution_sections.append(
                {
                    "title": f"{section_label} Solutions",
                    "spec": spec,
                    "layout": (rows, cols),
                    "items": solutions,
                    "start_index": start_index,
                }
            )
            start_index += count

        interior_pdf = build_interior_pdf(
            puzzle_sections=puzzle_sections,
            solution_sections=solution_sections,
            trim_size=(trim_w, trim_h),
            margin_in=margin_in,
            inside_margin_in=margins.inside_in,
            include_page_numbers=include_page_numbers,
            force_even_pages=True,
        )

        cover_pdf = None
        if include_cover:
            cover_pdf = build_cover_pdf(
                trim_size=(trim_w, trim_h),
                page_count=total_pages_even,
                bleed_in=bleed_in,
                spine_in=spine_in,
                safe_in=safe_in,
                title=cover_title,
                subtitle=cover_subtitle,
                author=cover_author,
                back_text=cover_back_text,
            )

    status.write("Done.")
    progress.progress(1.0)

    if warnings:
        st.warning(
            f"{len(warnings)} puzzles did not hit the exact target clue count. "
            "Closest valid puzzles were used instead."
        )
        with st.expander("Show clue count details"):
            for section_label, idx, target, actual, reason in warnings[:50]:
                if reason:
                    st.write(f"{section_label} - Puzzle {idx}: target {target}, actual {actual} ({reason})")
                else:
                    st.write(f"{section_label} - Puzzle {idx}: target {target}, actual {actual}")
            if len(warnings) > 50:
                st.write(f"...and {len(warnings) - 50} more.")

    st.success("PDFs generated.")
    st.download_button(
        "Download interior PDF",
        data=interior_pdf.getvalue(),
        file_name="sudoku_interior.pdf",
        mime="application/pdf",
    )

    if cover_pdf:
        st.download_button(
            "Download cover PDF",
            data=cover_pdf.getvalue(),
            file_name="sudoku_cover.pdf",
            mime="application/pdf",
        )

        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zf:
            zf.writestr("sudoku_interior.pdf", interior_pdf.getvalue())
            zf.writestr("sudoku_cover.pdf", cover_pdf.getvalue())
        st.download_button(
            "Download both as ZIP",
            data=zip_buffer.getvalue(),
            file_name="sudoku_book_files.zip",
            mime="application/zip",
        )

import math
import random
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import streamlit as st

from cover import build_cover_pdf
from pdf_utils import build_interior_pdf
from sudoku import generate_puzzles, spec_for_size


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
    margin_in = st.number_input("Interior margin (in)", min_value=0.25, max_value=1.5, value=0.5, step=0.05)
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
total_pages = puzzle_pages + solution_pages

st.write(
    "Configure your book and generate a print-ready interior PDF with puzzles and solutions. "
    "Optionally generate a KDP-sized cover PDF."
)
st.info(
    f"Total puzzles: {total_puzzles} | Estimated interior pages: {total_pages} "
    f"({puzzle_pages} puzzle pages + {solution_pages} solution pages)"
)

generate = st.button("Generate PDFs", type="primary")

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
            include_page_numbers=include_page_numbers,
        )

        cover_pdf = None
        if include_cover:
            cover_pdf = build_cover_pdf(
                trim_size=(trim_w, trim_h),
                page_count=total_pages,
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

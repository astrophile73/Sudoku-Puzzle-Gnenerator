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


def _layout_for_size(size, layout_map):
    return layout_map[size]


def _pages_needed(puzzle_count, rows, cols):
    per_page = max(1, rows * cols)
    return int(math.ceil(puzzle_count / per_page))


st.set_page_config(page_title="Sudoku Book Generator", layout="wide")
st.title("Sudoku Book Generator for Amazon KDP")

with st.sidebar:
    st.header("Puzzle Settings")
    size = st.selectbox("Sudoku size", [6, 9, 16], index=1)
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard", "Expert"], index=1)
    puzzle_count = st.number_input("Number of puzzles", min_value=1, max_value=2000, value=100, step=10)
    seed_text = st.text_input("Random seed (optional)", value="")

    st.header("Layout (Per Size)")
    rows_6 = st.number_input("6x6 rows per page", min_value=1, max_value=6, value=2, step=1, key="rows_6")
    cols_6 = st.number_input("6x6 cols per page", min_value=1, max_value=6, value=2, step=1, key="cols_6")
    rows_9 = st.number_input("9x9 rows per page", min_value=1, max_value=6, value=2, step=1, key="rows_9")
    cols_9 = st.number_input("9x9 cols per page", min_value=1, max_value=6, value=2, step=1, key="cols_9")
    rows_16 = st.number_input("16x16 rows per page", min_value=1, max_value=6, value=1, step=1, key="rows_16")
    cols_16 = st.number_input("16x16 cols per page", min_value=1, max_value=6, value=1, step=1, key="cols_16")

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

layout_map = {
    6: (int(rows_6), int(cols_6)),
    9: (int(rows_9), int(cols_9)),
    16: (int(rows_16), int(cols_16)),
}
rows, cols = _layout_for_size(size, layout_map)

puzzle_pages = _pages_needed(puzzle_count, rows, cols)
solution_pages = puzzle_pages
total_pages = puzzle_pages + solution_pages

st.write(
    "Configure your book and generate a print-ready interior PDF with puzzles and solutions. "
    "Optionally generate a KDP-sized cover PDF."
)
st.info(
    f"Estimated interior pages: {total_pages} "
    f"({puzzle_pages} puzzle pages + {solution_pages} solution pages)"
)

generate = st.button("Generate PDFs", type="primary")

if generate:
    rng = random.Random(seed_text) if seed_text else random.Random()
    spec = spec_for_size(size)

    progress = st.progress(0)
    status = st.empty()
    warnings = []

    def _progress_cb(done, total):
        progress.progress(min(1.0, done / max(1, total)))
        status.write(f"Generating puzzles {done}/{total}...")

    def _warn_cb(index, target, actual):
        warnings.append((index, target, actual))

    with st.spinner("Building puzzles and PDFs..."):
        puzzles, solutions = generate_puzzles(
            count=puzzle_count,
            spec=spec,
            difficulty=difficulty,
            rng=rng,
            progress_cb=_progress_cb,
            warn_cb=_warn_cb,
        )

        interior_pdf = build_interior_pdf(
            puzzles=puzzles,
            solutions=solutions,
            spec=spec,
            trim_size=(trim_w, trim_h),
            margin_in=margin_in,
            layout=(rows, cols),
            include_page_numbers=include_page_numbers,
            title="Sudoku Puzzles",
            solutions_title="Solutions",
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
            for idx, target, actual in warnings[:50]:
                st.write(f"Puzzle {idx}: target {target}, actual {actual}")
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

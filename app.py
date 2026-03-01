"""Sudoku Book Generator — Professional KDP-ready Streamlit application.

Tabs:
  1. Quick Generate  — 3-step wizard for fast book creation
  2. Advanced Settings — Full parameter control
  3. Batch Processing  — Generate multiple books at once
  4. Project Manager   — Save / load / manage configurations
"""
from __future__ import annotations

import math
import random
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

from batch_processor import (
    BatchBookSpec,
    create_batch_zip,
    process_batch,
)
from config_manager import (
    apply_template,
    config_from_json,
    config_to_json,
    get_template_names,
)
from cover import build_cover_pdf
from fonts import ensure_fonts_registered
from kdp_specs import (
    KDP_MIN_OUTSIDE_TOP_BOTTOM_IN,
    build_margin_spec_no_bleed,
    compute_even_page_count,
)
from pdf_utils import build_interior_pdf
from sudoku import generate_puzzles, spec_for_size
from ui_components import (
    inject_css,
    render_about_section,
    render_app_header,
    render_book_metrics,
    render_compliance_checklist,
    render_faq,
    render_kdp_resources,
    render_preflight_status,
    render_section_header,
    render_troubleshooting,
    step_indicator_html,
)
from validators import PreflightReport, estimate_book_cost, run_preflight

# ── Constants ─────────────────────────────────────────────────────────────────

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
TRIM_DICT = dict(TRIM_SIZES)
TRIM_LABELS = [label for label, _ in TRIM_SIZES]

SIZES = [6, 9, 16]
DIFFICULTIES = ["Easy", "Medium", "Hard", "Expert"]


# ── Helper utilities ──────────────────────────────────────────────────────────

def _layout_from_per_page(per_page: int):
    per_page = max(1, int(per_page))
    rows = max(1, int(math.floor(math.sqrt(per_page))))
    cols = int(math.ceil(per_page / rows))
    return rows, cols


def _pages_needed(puzzle_count: int, rows: int, cols: int) -> int:
    per_page = max(1, rows * cols)
    return int(math.ceil(puzzle_count / per_page))


def _compute_book_stats(counts, per_page_by_size):
    sections = []
    total_puzzles = 0
    puzzle_pages = 0
    for size in SIZES:
        rows, cols = _layout_from_per_page(per_page_by_size.get(size, 4))
        for difficulty in DIFFICULTIES:
            count = counts.get(size, {}).get(difficulty, 0)
            if count <= 0:
                continue
            puzzle_pages += _pages_needed(count, rows, cols)
            total_puzzles += count
            sections.append((size, difficulty, count, rows, cols))
    solution_pages = puzzle_pages
    raw_total = puzzle_pages + solution_pages
    even_pages = compute_even_page_count(raw_total)
    return sections, total_puzzles, raw_total, even_pages


def _run_preflight_for_state(counts, per_page_by_size, trim_label, margin_in,
                              extra_gutter_in, include_page_numbers):
    trim_w, trim_h = TRIM_DICT.get(trim_label, (6.0, 9.0))
    sections, total_puzzles, raw_pages, even_pages = _compute_book_stats(counts, per_page_by_size)
    margins = build_margin_spec_no_bleed(
        page_count_even=even_pages,
        outside_top_bottom_in=margin_in,
        extra_gutter_in=extra_gutter_in,
    )
    font_label = None
    font_error = None
    try:
        font_label = ensure_fonts_registered()
    except Exception as exc:
        font_error = str(exc)

    report = run_preflight(
        sections=sections,
        total_pages_even=even_pages,
        margins=margins,
        trim_w=trim_w,
        trim_h=trim_h,
        include_page_numbers=include_page_numbers,
        font_label=font_label,
        font_error=font_error,
    )
    return report, sections, total_puzzles, raw_pages, even_pages, margins, trim_w, trim_h


def _do_generate(counts, per_page_by_size, trim_label, margin_in, extra_gutter_in,
                 include_page_numbers, include_cover, cover_title, cover_subtitle,
                 cover_author, cover_back_text, bleed_in, spine_in, safe_in, seed_text,
                 pdf_title="", pdf_author="", pdf_subject="", pdf_keywords=""):
    """Core generation logic shared by Quick Generate and Advanced Settings tabs."""
    trim_w, trim_h = TRIM_DICT.get(trim_label, (6.0, 9.0))
    sections, total_puzzles, raw_pages, even_pages = _compute_book_stats(counts, per_page_by_size)

    if total_puzzles == 0:
        st.error("Please add at least one puzzle count to generate a book.")
        return

    margins = build_margin_spec_no_bleed(
        page_count_even=even_pages,
        outside_top_bottom_in=margin_in,
        extra_gutter_in=extra_gutter_in,
    )

    rng = random.Random(seed_text) if seed_text else random.Random()
    progress = st.progress(0)
    status = st.empty()
    warnings = []

    with st.spinner("Building puzzles and PDFs\u2026"):
        puzzle_sections = []
        solution_sections = []
        progress_state = {"done": 0}
        start_index = 0

        for size, difficulty, count, rows, cols in sections:
            section_label = f"{size}x{size} {difficulty}"
            spec = spec_for_size(size)
            section_state = {"done": 0}

            def _section_progress_cb(done, total, _label=section_label, _count=count):
                progress_state["done"] += done - section_state["done"]
                section_state["done"] = done
                progress.progress(min(1.0, progress_state["done"] / max(1, total_puzzles)))
                status.write(f"Generating {_label}: {done}/{_count}")

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
            puzzle_sections.append({
                "title": section_label,
                "spec": spec,
                "layout": (rows, cols),
                "items": puzzles,
                "start_index": start_index,
            })
            solution_sections.append({
                "title": f"{section_label} Solutions",
                "spec": spec,
                "layout": (rows, cols),
                "items": solutions,
                "start_index": start_index,
            })
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
                page_count=even_pages,
                bleed_in=bleed_in,
                spine_in=spine_in,
                safe_in=safe_in,
                title=cover_title,
                subtitle=cover_subtitle,
                author=cover_author,
                back_text=cover_back_text,
            )

    status.write("\u2705 Done!")
    progress.progress(1.0)

    if warnings:
        st.warning(
            f"{len(warnings)} puzzle(s) did not hit the exact target clue count. "
            "Closest valid puzzles were used instead."
        )
        with st.expander("Show clue count details"):
            for section_label, idx, target, actual, reason in warnings[:50]:
                msg = f"{section_label} \u2014 Puzzle {idx}: target {target}, actual {actual}"
                if reason:
                    msg += f" ({reason})"
                st.write(msg)
            if len(warnings) > 50:
                st.write(f"\u2026and {len(warnings) - 50} more.")

    st.success(f"\u2705 PDFs generated \u2014 {even_pages} pages, {total_puzzles} puzzles.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "\u2b07\ufe0f Interior PDF",
            data=interior_pdf.getvalue(),
            file_name="sudoku_interior.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    if cover_pdf:
        with col2:
            st.download_button(
                "\u2b07\ufe0f Cover PDF",
                data=cover_pdf.getvalue(),
                file_name="sudoku_cover.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col3:
            zip_buffer = BytesIO()
            with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zf:
                zf.writestr("sudoku_interior.pdf", interior_pdf.getvalue())
                zf.writestr("sudoku_cover.pdf", cover_pdf.getvalue())
            st.download_button(
                "\u2b07\ufe0f Both as ZIP",
                data=zip_buffer.getvalue(),
                file_name="sudoku_book_files.zip",
                mime="application/zip",
                use_container_width=True,
            )


# ── Page setup ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sudoku Book Generator",
    page_icon="\U0001f4da",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
render_app_header()
st.divider()

# ── Sidebar: About & Help ─────────────────────────────────────────────────────
with st.sidebar:
    render_about_section()
    render_kdp_resources()
    render_faq()
    render_troubleshooting()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_quick, tab_advanced, tab_batch, tab_project = st.tabs([
    "\u26a1 Quick Generate",
    "\u2699\ufe0f Advanced Settings",
    "\U0001f4e6 Batch Processing",
    "\U0001f4be Project Manager",
])


# ════════════════════════════════════════════════════════════════════════════
# Tab 1 — Quick Generate
# ════════════════════════════════════════════════════════════════════════════
with tab_quick:
    if "qg_step" not in st.session_state:
        st.session_state["qg_step"] = 1

    step = st.session_state["qg_step"]
    st.markdown(
        step_indicator_html(step, 3, ["Puzzle Mix", "Book Size", "Cover & Generate"]),
        unsafe_allow_html=True,
    )

    # ── Step 1: Puzzle Mix ────────────────────────────────────────────────
    if step == 1:
        render_section_header("Step 1 \u2014 Choose Your Puzzle Mix")

        template_col, _ = st.columns([2, 2])
        with template_col:
            template_name = st.selectbox(
                "Quick template",
                ["(none)"] + get_template_names(),
                key="qg_template",
                help="Load a pre-configured puzzle mix template.",
            )
            if st.button("Apply Template", key="qg_apply_template") and template_name != "(none)":
                tpl = apply_template(template_name)
                st.session_state["qg_config"] = tpl
                st.toast(f"Template '{template_name}' applied.", icon="\u2705")

        st.markdown("")

        qg_cfg = st.session_state.get("qg_config", {})
        qg_puzzles = qg_cfg.get("puzzle_settings", {}).get("puzzles", {})

        cols = st.columns(3)
        qg_counts = {}
        qg_per_page = {}
        for col, size in zip(cols, SIZES):
            with col:
                st.markdown(f"**{size}\xd7{size} Puzzles**")
                pp_default = qg_puzzles.get(size, {}).get("per_page", 4 if size != 16 else 1)
                qg_per_page[size] = st.number_input(
                    "Per page", min_value=1, max_value=36,
                    value=int(pp_default), step=1, key=f"qg_pp_{size}",
                )
                qg_counts[size] = {}
                for diff in DIFFICULTIES:
                    default = qg_puzzles.get(size, {}).get(diff, 0)
                    if size == 9 and diff == "Easy" and not qg_puzzles:
                        default = 10
                    qg_counts[size][diff] = st.number_input(
                        diff, min_value=0, max_value=2000,
                        value=int(default), step=5, key=f"qg_{size}_{diff}",
                    )

        if st.button("Next: Book Size \u2192", type="primary", key="qg_next1"):
            st.session_state["qg_counts"] = qg_counts
            st.session_state["qg_per_page"] = qg_per_page
            st.session_state["qg_step"] = 2
            st.rerun()

    # ── Step 2: Book Size ─────────────────────────────────────────────────
    elif step == 2:
        render_section_header("Step 2 \u2014 Choose Book Size & Margins")

        qg_cfg = st.session_state.get("qg_config", {})
        bs = qg_cfg.get("book_settings", {})

        trim_default_idx = (
            TRIM_LABELS.index(bs.get("trim_label", "6 x 9 in"))
            if bs.get("trim_label") in TRIM_LABELS else 4
        )
        qg_trim_label = st.selectbox("Trim size (KDP presets)", TRIM_LABELS, index=trim_default_idx, key="qg_trim")
        qg_margin_in = st.slider(
            "Outside/Top/Bottom margin (in)",
            min_value=KDP_MIN_OUTSIDE_TOP_BOTTOM_IN,
            max_value=1.5,
            value=float(bs.get("margin_in", 0.5)),
            step=0.05,
            key="qg_margin",
            help="KDP minimum is 0.25 in.",
        )
        qg_extra_gutter = st.slider(
            "Extra gutter (in)",
            min_value=0.0, max_value=1.0,
            value=float(bs.get("extra_gutter_in", 0.0)),
            step=0.05,
            key="qg_gutter",
        )
        qg_page_nums = st.checkbox(
            "Include page numbers",
            value=bool(bs.get("include_page_numbers", True)),
            key="qg_pgnums",
        )

        qg_counts = st.session_state.get("qg_counts", {s: {d: 0 for d in DIFFICULTIES} for s in SIZES})
        qg_per_page = st.session_state.get("qg_per_page", {s: 4 for s in SIZES})
        sections, total_puzzles, raw_pages, even_pages = _compute_book_stats(qg_counts, qg_per_page)
        margins = build_margin_spec_no_bleed(even_pages, qg_margin_in, qg_extra_gutter)

        st.markdown("")
        render_book_metrics(total_puzzles, raw_pages, even_pages, margins)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("\u2190 Back", key="qg_back2"):
                st.session_state["qg_step"] = 1
                st.rerun()
        with c2:
            if st.button("Next: Cover & Generate \u2192", type="primary", key="qg_next2"):
                st.session_state["qg_trim_label"] = qg_trim_label
                st.session_state["qg_margin_in"] = qg_margin_in
                st.session_state["qg_extra_gutter"] = qg_extra_gutter
                st.session_state["qg_page_nums"] = qg_page_nums
                st.session_state["qg_step"] = 3
                st.rerun()

    # ── Step 3: Cover & Generate ──────────────────────────────────────────
    elif step == 3:
        render_section_header("Step 3 \u2014 Cover & Generate")

        qg_cfg = st.session_state.get("qg_config", {})
        cs = qg_cfg.get("cover_settings", {})

        qg_include_cover = st.checkbox(
            "Generate cover PDF",
            value=bool(cs.get("include_cover", True)),
            key="qg_cover_inc",
        )
        if qg_include_cover:
            col_a, col_b = st.columns(2)
            with col_a:
                qg_cover_title = st.text_input("Title", value=cs.get("title", "Sudoku Puzzle Book"), key="qg_ctitle")
                qg_cover_subtitle = st.text_input("Subtitle", value=cs.get("subtitle", "Brain-Teasing Puzzles"), key="qg_csub")
                qg_cover_author = st.text_input("Author", value=cs.get("author", "Your Name"), key="qg_cauthor")
            with col_b:
                qg_cover_back = st.text_area(
                    "Back cover text",
                    value=cs.get("back_text", "Enjoy hours of entertainment with these Sudoku puzzles."),
                    height=100, key="qg_cback",
                )
                qg_spine_in = st.number_input(
                    "Spine width (in)",
                    min_value=0.0, max_value=2.0,
                    value=float(cs.get("spine_in", 0.5)), step=0.01,
                    key="qg_spine",
                    help="pages \xd7 0.002252 in (white 60#) or pages \xd7 0.0025 in (cream 60#).",
                )
        else:
            qg_cover_title = cs.get("title", "Sudoku Puzzle Book")
            qg_cover_subtitle = cs.get("subtitle", "")
            qg_cover_author = cs.get("author", "Your Name")
            qg_cover_back = cs.get("back_text", "")
            qg_spine_in = float(cs.get("spine_in", 0.5))

        qg_seed = st.text_input("Random seed (optional)", value="", key="qg_seed",
                                help="Leave blank for a random book each time.")

        counts = st.session_state.get("qg_counts", {s: {d: 0 for d in DIFFICULTIES} for s in SIZES})
        per_page = st.session_state.get("qg_per_page", {s: 4 for s in SIZES})
        trim_label = st.session_state.get("qg_trim_label", "6 x 9 in")
        margin_in = st.session_state.get("qg_margin_in", 0.5)
        extra_gutter = st.session_state.get("qg_extra_gutter", 0.0)
        page_nums = st.session_state.get("qg_page_nums", True)

        report, sections, total_puzzles, raw_pages, even_pages, margins, trim_w, trim_h = \
            _run_preflight_for_state(counts, per_page, trim_label, margin_in, extra_gutter, page_nums)

        st.markdown("")
        render_book_metrics(total_puzzles, raw_pages, even_pages, margins)
        render_preflight_status(report)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("\u2190 Back", key="qg_back3"):
                st.session_state["qg_step"] = 2
                st.rerun()
        with c2:
            if st.button(
                "\U0001f680 Generate Book",
                type="primary",
                key="qg_generate",
                disabled=not report.passed,
            ):
                _do_generate(
                    counts=counts,
                    per_page_by_size=per_page,
                    trim_label=trim_label,
                    margin_in=margin_in,
                    extra_gutter_in=extra_gutter,
                    include_page_numbers=page_nums,
                    include_cover=qg_include_cover,
                    cover_title=qg_cover_title,
                    cover_subtitle=qg_cover_subtitle,
                    cover_author=qg_cover_author,
                    cover_back_text=qg_cover_back,
                    bleed_in=float(cs.get("bleed_in", 0.125)),
                    spine_in=qg_spine_in,
                    safe_in=float(cs.get("safe_in", 0.25)),
                    seed_text=qg_seed,
                )

        if st.button("\u21a9 Start Over", key="qg_restart"):
            st.session_state["qg_step"] = 1
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# Tab 2 — Advanced Settings
# ════════════════════════════════════════════════════════════════════════════
with tab_advanced:
    render_section_header("Advanced Settings")

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        render_section_header("Puzzle Settings")
        adv_seed = st.text_input("Random seed (optional)", value="", key="adv_seed")

        adv_counts = {size: {} for size in SIZES}
        adv_per_page = {}
        for size in SIZES:
            with st.expander(f"{size}\xd7{size} settings", expanded=(size == 9)):
                pp_default = 1 if size == 16 else 4
                adv_per_page[size] = st.number_input(
                    "Puzzles per page", min_value=1, max_value=36,
                    value=pp_default, step=1, key=f"adv_pp_{size}",
                )
                for diff in DIFFICULTIES:
                    default = 10 if (size == 9 and diff == "Easy") else 0
                    adv_counts[size][diff] = st.number_input(
                        f"{diff} puzzles", min_value=0, max_value=2000,
                        value=default, step=5, key=f"adv_{size}_{diff}",
                    )

        render_section_header("PDF Metadata")
        adv_pdf_title = st.text_input("PDF Title", value="Sudoku Puzzle Book", key="adv_pdftitle")
        adv_pdf_author = st.text_input("PDF Author", value="", key="adv_pdfauthor")
        adv_pdf_subject = st.text_input("PDF Subject", value="Sudoku Puzzle Book", key="adv_pdfsubject")
        adv_pdf_keywords = st.text_input(
            "PDF Keywords", value="sudoku, puzzle, brain training", key="adv_pdfkw",
        )

    with col_right:
        render_section_header("Book Size")
        adv_trim_label = st.selectbox("Trim size", TRIM_LABELS, index=4, key="adv_trim")
        adv_margin_in = st.number_input(
            "Outside/Top/Bottom margin (in)",
            min_value=KDP_MIN_OUTSIDE_TOP_BOTTOM_IN, max_value=1.5,
            value=0.5, step=0.05, key="adv_margin",
            help="KDP minimum is 0.25 in.",
        )
        adv_extra_gutter = st.number_input(
            "Extra gutter (inside) (in)",
            min_value=0.0, max_value=1.0,
            value=0.0, step=0.05, key="adv_gutter",
            help="Added on top of the KDP-required inside margin.",
        )
        adv_page_nums = st.checkbox("Include page numbers", value=True, key="adv_pgnums")

        render_section_header("Cover Settings")
        adv_include_cover = st.checkbox("Generate cover PDF", value=True, key="adv_cover")
        adv_cover_title = st.text_input("Title", value="Sudoku Puzzle Book", key="adv_ctitle")
        adv_cover_subtitle = st.text_input("Subtitle", value="Brain-Teasing Puzzles", key="adv_csub")
        adv_cover_author = st.text_input("Author", value="Your Name", key="adv_cauthor")
        adv_cover_back = st.text_area(
            "Back cover text",
            value=(
                "Enjoy hours of entertainment with a curated set of Sudoku puzzles. "
                "Perfect for travel, relaxation, and daily brain training."
            ),
            height=100, key="adv_cback",
        )
        adv_bleed = st.number_input(
            "Bleed (in)", min_value=0.0, max_value=0.25, value=0.125, step=0.01, key="adv_bleed",
        )
        adv_spine = st.number_input(
            "Spine width (in)", min_value=0.0, max_value=2.0, value=0.5, step=0.01,
            key="adv_spine",
            help="KDP: pages \xd7 0.002252 in (white 60#) or pages \xd7 0.0025 in (cream 60#).",
        )
        adv_safe = st.number_input(
            "Safe margin (in)", min_value=0.1, max_value=0.5, value=0.25, step=0.01,
            key="adv_safe",
        )

    st.divider()
    report, sections, total_puzzles, raw_pages, even_pages, margins, trim_w, trim_h = \
        _run_preflight_for_state(
            adv_counts, adv_per_page, adv_trim_label, adv_margin_in, adv_extra_gutter, adv_page_nums
        )

    render_book_metrics(total_puzzles, raw_pages, even_pages, margins)
    st.markdown("")

    col_pf, col_cl = st.columns(2)
    with col_pf:
        render_preflight_status(report)
    with col_cl:
        with st.expander("KDP Compliance Checklist"):
            render_compliance_checklist(report, even_pages, margins)

    with st.expander("\U0001f4ca Estimated Book Cost (KDP B&W Paperback)"):
        cost = estimate_book_cost(even_pages, trim_w, trim_h)
        st.write(f"**Printing cost estimate:** ${cost['printing_cost_usd']:.2f} USD")
        st.write(f"**Size category:** {cost['size_category']}")
        st.caption(cost["note"])

    st.markdown("")
    if st.button(
        "\U0001f680 Generate PDFs",
        type="primary",
        key="adv_generate",
        disabled=not report.passed,
    ):
        _do_generate(
            counts=adv_counts,
            per_page_by_size=adv_per_page,
            trim_label=adv_trim_label,
            margin_in=adv_margin_in,
            extra_gutter_in=adv_extra_gutter,
            include_page_numbers=adv_page_nums,
            include_cover=adv_include_cover,
            cover_title=adv_cover_title,
            cover_subtitle=adv_cover_subtitle,
            cover_author=adv_cover_author,
            cover_back_text=adv_cover_back,
            bleed_in=adv_bleed,
            spine_in=adv_spine,
            safe_in=adv_safe,
            seed_text=adv_seed,
            pdf_title=adv_pdf_title,
            pdf_author=adv_pdf_author,
            pdf_subject=adv_pdf_subject,
            pdf_keywords=adv_pdf_keywords,
        )


# ════════════════════════════════════════════════════════════════════════════
# Tab 3 — Batch Processing
# ════════════════════════════════════════════════════════════════════════════
with tab_batch:
    render_section_header("Batch Processing")
    st.write(
        "Define multiple books and generate them all at once. "
        "Downloads a ZIP archive with all PDFs."
    )

    if "batch_books" not in st.session_state:
        st.session_state["batch_books"] = [
            {
                "name": "Book 1",
                "trim_label": "6 x 9 in",
                "seed": "",
                "puzzles": {9: {"Easy": 50, "Medium": 0, "Hard": 0, "Expert": 0}},
                "per_page": {9: 4},
                "margin_in": 0.5,
                "extra_gutter_in": 0.0,
                "include_page_numbers": True,
                "include_cover": True,
                "cover_title": "Sudoku Book 1",
                "cover_subtitle": "",
                "cover_author": "Your Name",
                "cover_back_text": "",
                "bleed_in": 0.125,
                "spine_in": 0.5,
                "safe_in": 0.25,
            }
        ]

    if st.button("\u2795 Add Book", key="batch_add"):
        n = len(st.session_state["batch_books"]) + 1
        st.session_state["batch_books"].append({
            "name": f"Book {n}",
            "trim_label": "6 x 9 in",
            "seed": "",
            "puzzles": {9: {"Easy": 50, "Medium": 0, "Hard": 0, "Expert": 0}},
            "per_page": {9: 4},
            "margin_in": 0.5,
            "extra_gutter_in": 0.0,
            "include_page_numbers": True,
            "include_cover": True,
            "cover_title": f"Sudoku Book {n}",
            "cover_subtitle": "",
            "cover_author": "Your Name",
            "cover_back_text": "",
            "bleed_in": 0.125,
            "spine_in": 0.5,
            "safe_in": 0.25,
        })
        st.rerun()

    books_to_remove = []
    for i, book in enumerate(st.session_state["batch_books"]):
        with st.expander(f"\U0001f4d6 {book['name']}", expanded=(i == 0)):
            b_col1, b_col2, b_col3 = st.columns([2, 2, 1])
            with b_col1:
                book["name"] = st.text_input("Book name", value=book["name"], key=f"bn_{i}")
                book["trim_label"] = st.selectbox(
                    "Trim size", TRIM_LABELS,
                    index=TRIM_LABELS.index(book["trim_label"]) if book["trim_label"] in TRIM_LABELS else 4,
                    key=f"bt_{i}",
                )
                book["seed"] = st.text_input("Seed (optional)", value=book.get("seed", ""), key=f"bs_{i}")
            with b_col2:
                book["cover_title"] = st.text_input("Cover title", value=book.get("cover_title", ""), key=f"bct_{i}")
                book["cover_author"] = st.text_input("Author", value=book.get("cover_author", "Your Name"), key=f"bca_{i}")
                book["spine_in"] = st.number_input("Spine (in)", 0.0, 2.0, float(book.get("spine_in", 0.5)), 0.01, key=f"bsp_{i}")
            with b_col3:
                book["include_cover"] = st.checkbox("Cover PDF", value=book.get("include_cover", True), key=f"bic_{i}")
                book["include_page_numbers"] = st.checkbox("Page #s", value=book.get("include_page_numbers", True), key=f"bpn_{i}")

            st.markdown("**Puzzle counts (9\xd79)**")
            b_p9 = book.get("puzzles", {}).get(9, {})
            p_cols = st.columns(4)
            for col, diff in zip(p_cols, DIFFICULTIES):
                with col:
                    val = b_p9.get(diff, 0)
                    new_val = st.number_input(diff, 0, 2000, int(val), 5, key=f"b9_{diff}_{i}")
                    if 9 not in book["puzzles"]:
                        book["puzzles"][9] = {}
                    book["puzzles"][9][diff] = new_val

            if st.button(f"\U0001f5d1 Remove Book {i+1}", key=f"rm_{i}"):
                books_to_remove.append(i)

    for idx in sorted(books_to_remove, reverse=True):
        st.session_state["batch_books"].pop(idx)
    if books_to_remove:
        st.rerun()

    st.divider()
    if st.button("\U0001f680 Generate All Books", type="primary", key="batch_gen"):
        specs = []
        for book in st.session_state["batch_books"]:
            trim_w, trim_h = TRIM_DICT.get(book.get("trim_label", "6 x 9 in"), (6.0, 9.0))
            specs.append(BatchBookSpec(
                name=book["name"],
                seed=book.get("seed", ""),
                puzzles={int(k): {d: int(v) for d, v in diffs.items()} for k, diffs in book.get("puzzles", {}).items()},
                per_page={int(k): int(v) for k, v in book.get("per_page", {9: 4}).items()},
                trim_label=book.get("trim_label", "6 x 9 in"),
                trim_w=trim_w,
                trim_h=trim_h,
                margin_in=float(book.get("margin_in", 0.5)),
                extra_gutter_in=float(book.get("extra_gutter_in", 0.0)),
                include_page_numbers=bool(book.get("include_page_numbers", True)),
                include_cover=bool(book.get("include_cover", True)),
                cover_title=book.get("cover_title", ""),
                cover_subtitle=book.get("cover_subtitle", ""),
                cover_author=book.get("cover_author", "Your Name"),
                cover_back_text=book.get("cover_back_text", ""),
                bleed_in=float(book.get("bleed_in", 0.125)),
                spine_in=float(book.get("spine_in", 0.5)),
                safe_in=float(book.get("safe_in", 0.25)),
            ))

        batch_progress = st.progress(0)
        batch_status = st.empty()

        def _batch_progress(done, total, name):
            batch_progress.progress(min(1.0, done / max(1, total)))
            batch_status.write(f"Processing {name}\u2026 ({done}/{total})")

        with st.spinner("Generating batch\u2026"):
            results = process_batch(specs, progress_cb=_batch_progress)

        batch_progress.progress(1.0)
        batch_status.write("\u2705 Batch complete!")

        errors = [r for r in results if r.error]
        successes = [r for r in results if not r.error]

        if errors:
            st.warning(f"{len(errors)} book(s) had errors:")
            for r in errors:
                st.error(f"**{r.name}**: {r.error}")

        if successes:
            st.success(f"\u2705 {len(successes)} book(s) generated successfully.")
            zip_data = create_batch_zip(successes)
            st.download_button(
                "\u2b07\ufe0f Download All as ZIP",
                data=zip_data.getvalue(),
                file_name="sudoku_batch.zip",
                mime="application/zip",
                use_container_width=True,
            )


# ════════════════════════════════════════════════════════════════════════════
# Tab 4 — Project Manager
# ════════════════════════════════════════════════════════════════════════════
with tab_project:
    render_section_header("Project Manager")
    st.write(
        "Save your current settings as a JSON project file, "
        "load a previously saved project, or start from a quick template."
    )

    pm_col1, pm_col2 = st.columns(2)

    with pm_col1:
        render_section_header("Save Project")
        pm_save_name = st.text_input("Project name", value="my_sudoku_book", key="pm_savename")

        def _build_current_config() -> dict:
            puzzles_cfg: dict = {}
            for size in SIZES:
                per_p = int(st.session_state.get(f"adv_pp_{size}", 4 if size != 16 else 1))
                puzzles_cfg[size] = {"per_page": per_p}
                for diff in DIFFICULTIES:
                    puzzles_cfg[size][diff] = int(st.session_state.get(f"adv_{size}_{diff}", 0))
            return {
                "version": "1.0",
                "puzzle_settings": {
                    "seed": st.session_state.get("adv_seed", ""),
                    "puzzles": puzzles_cfg,
                },
                "book_settings": {
                    "trim_label": st.session_state.get("adv_trim", "6 x 9 in"),
                    "margin_in": float(st.session_state.get("adv_margin", 0.5)),
                    "extra_gutter_in": float(st.session_state.get("adv_gutter", 0.0)),
                    "include_page_numbers": bool(st.session_state.get("adv_pgnums", True)),
                },
                "cover_settings": {
                    "include_cover": bool(st.session_state.get("adv_cover", True)),
                    "title": st.session_state.get("adv_ctitle", "Sudoku Puzzle Book"),
                    "subtitle": st.session_state.get("adv_csub", ""),
                    "author": st.session_state.get("adv_cauthor", "Your Name"),
                    "back_text": st.session_state.get("adv_cback", ""),
                    "bleed_in": float(st.session_state.get("adv_bleed", 0.125)),
                    "spine_in": float(st.session_state.get("adv_spine", 0.5)),
                    "safe_in": float(st.session_state.get("adv_safe", 0.25)),
                },
                "pdf_metadata": {
                    "title": st.session_state.get("adv_pdftitle", ""),
                    "author": st.session_state.get("adv_pdfauthor", ""),
                    "subject": st.session_state.get("adv_pdfsubject", ""),
                    "keywords": st.session_state.get("adv_pdfkw", ""),
                },
            }

        if st.button("\U0001f4be Export Config as JSON", key="pm_export"):
            cfg = _build_current_config()
            json_str = config_to_json(cfg)
            st.download_button(
                "\u2b07\ufe0f Download JSON",
                data=json_str,
                file_name=f"{pm_save_name}.json",
                mime="application/json",
                use_container_width=True,
            )

    with pm_col2:
        render_section_header("Load Project")
        uploaded = st.file_uploader(
            "Upload a saved project JSON",
            type=["json"],
            key="pm_upload",
            help="Load a previously exported project configuration.",
        )
        if uploaded is not None:
            try:
                loaded_cfg = config_from_json(uploaded.read().decode("utf-8"))
                st.session_state["qg_config"] = loaded_cfg
                st.success(
                    "\u2705 Project loaded! Switch to **Quick Generate** or **Advanced Settings** to use it."
                )
                with st.expander("Preview loaded config"):
                    st.json(loaded_cfg)
            except Exception as exc:
                st.error(f"Failed to load project: {exc}")

    st.divider()
    render_section_header("Quick Templates")
    st.write("Start from a pre-built template. Loads into Quick Generate.")

    tpl_cols = st.columns(3)
    template_names = get_template_names()
    for i, tname in enumerate(template_names):
        with tpl_cols[i % 3]:
            st.markdown(f'<div class="kdp-card"><b>{tname}</b></div>', unsafe_allow_html=True)
            if st.button(f"Load '{tname}'", key=f"tpl_{i}"):
                st.session_state["qg_config"] = apply_template(tname)
                st.session_state["qg_step"] = 1
                st.success(f"Template '{tname}' loaded \u2014 switch to Quick Generate.")

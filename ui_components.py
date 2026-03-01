"""Reusable UI building blocks for the Sudoku Book Generator Streamlit app."""
from __future__ import annotations

import streamlit as st

from styles import get_app_css
from validators import PreflightReport, get_kdp_compliance_checklist

APP_VERSION = "2.0.0"


def inject_css() -> None:
    """Inject custom CSS into the Streamlit page."""
    st.markdown(get_app_css(), unsafe_allow_html=True)


def render_app_header() -> None:
    """Render the branded application header."""
    st.markdown(
        f"""
        <div class="app-header">
            <div>
                <div class="app-title">
                    📚 Sudoku Book Generator
                    <span class="app-version">v{APP_VERSION}</span>
                </div>
                <div class="app-subtitle">
                    Professional KDP-ready puzzle book creator for Amazon Kindle Direct Publishing
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_book_metrics(total_puzzles: int, raw_pages: int, even_pages: int, margins) -> None:
    """Render a row of book metric boxes."""
    cols = st.columns(4)
    metrics = [
        ("Total Puzzles", str(total_puzzles)),
        ("Raw Pages", str(raw_pages)),
        ("Print Pages", str(even_pages)),
        ("Gutter", f"{margins.inside_in:.3f} in"),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-box">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_preflight_status(report: PreflightReport) -> None:
    """Render the KDP preflight pass/fail status and details."""
    if report.passed:
        badge_class = "badge-warn" if report.warnings else "badge-pass"
        st.markdown(
            f'<span class="{badge_class}">✅ KDP Preflight: {report.status_label}</span>',
            unsafe_allow_html=True,
        )
        for msg in report.info:
            st.caption(f"ℹ️ {msg}")
        for msg in report.warnings:
            st.caption(f"⚠️ {msg}")
    else:
        st.markdown(
            '<span class="badge-fail">❌ KDP Preflight: FAIL</span>',
            unsafe_allow_html=True,
        )
        for msg in report.errors:
            st.error(f"• {msg}")


def render_compliance_checklist(
    report: PreflightReport,
    total_pages_even: int,
    margins,
) -> None:
    """Render a KDP compliance checklist with pass/fail indicators."""
    items = get_kdp_compliance_checklist(report, total_pages_even, margins)
    lines = []
    for item in items:
        icon = "✅" if item["passed"] else "❌"
        cls = "check-pass" if item["passed"] else "check-fail"
        lines.append(
            f'<div class="check-item {cls}">{icon} <b>{item["label"]}</b>: {item["value"]}</div>'
        )
    st.markdown("\n".join(lines), unsafe_allow_html=True)


def render_section_header(text: str) -> None:
    """Render a styled section header."""
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def render_help_expander(title: str, content: str) -> None:
    """Render a collapsible help section."""
    with st.expander(f"❓ {title}"):
        st.markdown(content)


def render_kdp_resources() -> None:
    """Render links to KDP resources."""
    with st.expander("🔗 KDP Resources & Guidelines"):
        st.markdown(
            """
            - [KDP Paperback Formatting Guide](https://kdp.amazon.com/en_US/help/topic/G201834190)
            - [KDP Manuscript Templates](https://kdp.amazon.com/en_US/help/topic/G201834230)
            - [KDP Royalty Calculator](https://kdp.amazon.com/en_US/help/topic/G200645550)
            - [KDP Cover Creator](https://kdp.amazon.com/en_US/help/topic/G200645690)
            - [KDP Print Quality Guide](https://kdp.amazon.com/en_US/help/topic/G201816450)
            """
        )


def render_about_section() -> None:
    """Render the about/info section in a sidebar expander."""
    with st.expander("ℹ️ About this app"):
        st.markdown(
            f"""
            **Sudoku Book Generator** v{APP_VERSION}

            Generate print-ready Sudoku puzzle books for Amazon KDP with:
            - 6×6, 9×9, and 16×16 puzzle sizes
            - Easy, Medium, Hard, Expert difficulties
            - Proper KDP margins, gutter, and bleed
            - Embedded fonts for print-quality PDFs
            - Full cover with spine and bleed guides

            *Always validate output PDFs with current KDP specifications before publishing.*
            """
        )


def render_faq() -> None:
    """Render a FAQ section."""
    with st.expander("❓ FAQ"):
        st.markdown(
            """
            **Q: What spine width should I enter?**
            A: KDP spine width = page count × paper thickness.
            For standard white (60# paper): pages × 0.002252 in.
            For cream (60# paper): pages × 0.0025 in.

            **Q: Why does my inside margin seem large?**
            A: KDP requires larger gutter margins for thicker books to ensure text stays readable
            near the binding. This is automatically calculated from your page count.

            **Q: Can I use color in my book?**
            A: This app generates black & white PDFs. KDP also offers color printing at a higher cost.

            **Q: What DPI does the output PDF use?**
            A: The PDF is vector-based (scalable), so it prints at any DPI including 300 DPI+.

            **Q: How do I find my barcode/ISBN area?**
            A: Leave the lower-right area of the back cover clear for the KDP barcode.
            """
        )


def render_troubleshooting() -> None:
    """Render a troubleshooting section."""
    with st.expander("🔧 Troubleshooting"):
        st.markdown(
            """
            **Preflight FAIL — page count too low:**
            Increase puzzle counts so the total interior pages reach 24 (KDP minimum).

            **Preflight FAIL — cells too small:**
            Reduce puzzles-per-page, switch to a larger trim size, or use a smaller puzzle grid size.

            **Font warning:**
            Add `assets/fonts/NotoSans-Regular.ttf` and `assets/fonts/NotoSans-Bold.ttf` for
            guaranteed font embedding. The app falls back to system fonts (DejaVu/Arial).

            **PDF not downloading:**
            Try a different browser. Some corporate proxies block large downloads.

            **Puzzles take too long:**
            16×16 puzzles especially can take time. Reduce count or use Easy difficulty.
            """
        )


def step_indicator_html(current_step: int, total_steps: int, labels: list[str]) -> str:
    """Generate HTML for a step indicator."""
    parts = []
    for i, label in enumerate(labels):
        step_num = i + 1
        if step_num < current_step:
            cls = "step-dot-done"
            icon = "✓"
        elif step_num == current_step:
            cls = "step-dot-active"
            icon = str(step_num)
        else:
            cls = ""
            icon = str(step_num)
        parts.append(f'<div class="step-dot {cls}" title="{label}">{icon}</div>')
        if i < len(labels) - 1:
            parts.append('<div class="step-line"></div>')
    return f'<div class="step-indicator">{"".join(parts)}</div>'

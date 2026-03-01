"""Enhanced validation functions for KDP compliance checks."""
from __future__ import annotations

from dataclasses import dataclass, field

from kdp_specs import (
    KDP_MIN_OUTSIDE_TOP_BOTTOM_IN,
    build_margin_spec_no_bleed,
    compute_even_page_count,
    required_inside_margin_no_bleed,
    validate_page_count,
)


@dataclass
class PreflightReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    @property
    def status_label(self) -> str:
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "PASS with warnings"
        return "PASS"


def run_preflight(
    sections: list,
    total_pages_even: int,
    margins,
    trim_w: float,
    trim_h: float,
    include_page_numbers: bool,
    font_label: str | None,
    font_error: str | None,
) -> PreflightReport:
    report = PreflightReport()

    if font_error:
        report.errors.append(f"Fonts: {font_error}")
    elif font_label:
        report.info.append(f"Embedded fonts: {font_label}")

    report.errors.extend(validate_page_count(total_pages_even))

    if margins.outside_in < KDP_MIN_OUTSIDE_TOP_BOTTOM_IN:
        report.errors.append("Outside/Top/Bottom margin is below 0.25 in.")

    required_inside = required_inside_margin_no_bleed(total_pages_even)
    if margins.inside_in < required_inside:
        report.errors.append(
            f"Inside (gutter) margin {margins.inside_in:.3f} in is below KDP requirement "
            f"of {required_inside:.3f} in for {total_pages_even} pages."
        )

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
        report.errors.append("Margins are too large for this trim size.")
    else:
        for size, difficulty, count, rows, cols in sections:
            avail_h = avail_h_total - header_h - footer_h
            cell_w = avail_w / cols
            cell_h = avail_h / rows
            grid_size = min(cell_w, cell_h - label_h) - padding
            if grid_size <= 0:
                report.errors.append(
                    f"{size}x{size} {difficulty}: layout {rows}x{cols} does not fit. "
                    "Reduce puzzles-per-page or use a larger trim size."
                )
                continue
            cell = grid_size / size
            scale = 0.55 * (0.85 if size >= 10 else 1.0)
            if cell * scale < 7.0:
                report.errors.append(
                    f"{size}x{size} {difficulty}: cells are too small for 7pt minimum. "
                    "Reduce puzzles-per-page or increase trim size."
                )

    return report


def estimate_book_cost(page_count: int, trim_w: float, trim_h: float) -> dict:
    """Rough cost estimate for KDP black & white paperback."""
    fixed = 0.85
    per_page = 0.012
    printing_cost = fixed + per_page * page_count

    area = trim_w * trim_h
    if area <= 32:
        size_category = "Standard (≤5.5×8.5)"
    elif area <= 54:
        size_category = "Mid (6×9)"
    else:
        size_category = "Large (≥7×10)"

    return {
        "printing_cost_usd": round(printing_cost, 2),
        "size_category": size_category,
        "page_count": page_count,
        "note": "Estimate only. Verify with KDP royalty calculator.",
    }


def get_kdp_compliance_checklist(
    report: PreflightReport,
    total_pages_even: int,
    margins,
) -> list[dict]:
    """Returns a list of KDP compliance items with pass/fail status."""
    required_inside = required_inside_margin_no_bleed(total_pages_even)
    items = [
        {
            "label": "Page count (24–828)",
            "passed": 24 <= total_pages_even <= 828,
            "value": str(total_pages_even),
        },
        {
            "label": f"Outside margin ≥ {KDP_MIN_OUTSIDE_TOP_BOTTOM_IN} in",
            "passed": margins.outside_in >= KDP_MIN_OUTSIDE_TOP_BOTTOM_IN,
            "value": f"{margins.outside_in:.3f} in",
        },
        {
            "label": f"Inside (gutter) margin ≥ {required_inside:.3f} in",
            "passed": margins.inside_in >= required_inside,
            "value": f"{margins.inside_in:.3f} in",
        },
        {
            "label": "Fonts embedded",
            "passed": report.font_ok if hasattr(report, "font_ok") else (not any("Font" in e for e in report.errors)),
            "value": "Yes" if not any("Font" in e for e in report.errors) else "No",
        },
    ]
    return items

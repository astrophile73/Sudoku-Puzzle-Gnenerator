from __future__ import annotations

from dataclasses import dataclass


KDP_MIN_OUTSIDE_TOP_BOTTOM_IN = 0.25

# Paperback, black & white, no-bleed. Inside (gutter) minimum depends on page count.
# Page count should be even (KDP rounds up for printing).
KDP_INSIDE_GUTTER_TABLE = [
    (24, 150, 0.375),
    (151, 300, 0.5),
    (301, 500, 0.625),
    (501, 700, 0.75),
    (701, 828, 0.875),
]


def compute_even_page_count(page_count: int) -> int:
    if page_count <= 0:
        return 0
    return page_count if page_count % 2 == 0 else page_count + 1


def required_inside_margin_no_bleed(page_count_even: int) -> float:
    if page_count_even <= 0:
        return 0.0
    for lo, hi, gutter in KDP_INSIDE_GUTTER_TABLE:
        if lo <= page_count_even <= hi:
            return gutter
    # If outside the table, fall back to the max known value; caller should still validate.
    return KDP_INSIDE_GUTTER_TABLE[-1][2]


@dataclass(frozen=True)
class InteriorMarginSpec:
    outside_in: float
    top_in: float
    bottom_in: float
    inside_in: float


def build_margin_spec_no_bleed(
    page_count_even: int,
    outside_top_bottom_in: float,
    extra_gutter_in: float,
) -> InteriorMarginSpec:
    outside = max(KDP_MIN_OUTSIDE_TOP_BOTTOM_IN, float(outside_top_bottom_in))
    required_inside = required_inside_margin_no_bleed(page_count_even)
    inside = max(required_inside, outside) + max(0.0, float(extra_gutter_in))
    return InteriorMarginSpec(
        outside_in=outside,
        top_in=outside,
        bottom_in=outside,
        inside_in=inside,
    )


def validate_page_count(page_count_even: int) -> list[str]:
    errors: list[str] = []
    if page_count_even < 24:
        errors.append("KDP paperback minimum is 24 pages. Increase puzzle counts.")
    if page_count_even > 828:
        errors.append("KDP paperback maximum is 828 pages. Reduce puzzle counts.")
    return errors


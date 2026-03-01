"""Batch processing logic for generating multiple Sudoku books."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Callable
from zipfile import ZIP_DEFLATED, ZipFile

from cover import build_cover_pdf
from fonts import ensure_fonts_registered
from kdp_specs import (
    build_margin_spec_no_bleed,
    compute_even_page_count,
    required_inside_margin_no_bleed,
)
from pdf_utils import build_interior_pdf
from sudoku import generate_puzzles, spec_for_size


SIZES = [6, 9, 16]
DIFFICULTIES = ["Easy", "Medium", "Hard", "Expert"]


def _layout_from_per_page(per_page: int):
    per_page = max(1, int(per_page))
    rows = max(1, int(math.floor(math.sqrt(per_page))))
    cols = int(math.ceil(per_page / rows))
    return rows, cols


def _pages_needed(puzzle_count: int, rows: int, cols: int) -> int:
    per_page = max(1, rows * cols)
    return int(math.ceil(puzzle_count / per_page))


@dataclass
class BatchBookSpec:
    """Specification for a single book in a batch."""
    name: str
    seed: str = ""
    # puzzles[size][difficulty] = count
    puzzles: dict[int, dict[str, int]] = field(default_factory=dict)
    per_page: dict[int, int] = field(default_factory=dict)
    trim_label: str = "6 x 9 in"
    trim_w: float = 6.0
    trim_h: float = 9.0
    margin_in: float = 0.5
    extra_gutter_in: float = 0.0
    include_page_numbers: bool = True
    include_cover: bool = True
    cover_title: str = "Sudoku Puzzle Book"
    cover_subtitle: str = ""
    cover_author: str = "Your Name"
    cover_back_text: str = ""
    bleed_in: float = 0.125
    spine_in: float = 0.5
    safe_in: float = 0.25


@dataclass
class BatchResult:
    """Result for one book in a batch."""
    name: str
    interior_pdf: BytesIO | None = None
    cover_pdf: BytesIO | None = None
    error: str | None = None
    warnings: list = field(default_factory=list)
    page_count: int = 0


def process_batch(
    specs: list[BatchBookSpec],
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> list[BatchResult]:
    """
    Generate PDFs for a list of BatchBookSpec entries.

    progress_cb(done_books, total_books, current_book_name)
    """
    ensure_fonts_registered()
    results: list[BatchResult] = []
    total = len(specs)

    for book_idx, spec in enumerate(specs):
        if progress_cb:
            progress_cb(book_idx, total, spec.name)

        result = BatchResult(name=spec.name)
        try:
            rng = random.Random(spec.seed) if spec.seed else random.Random()

            sections = []
            for size in SIZES:
                per_page = spec.per_page.get(size, 4 if size != 16 else 1)
                rows, cols = _layout_from_per_page(per_page)
                for difficulty in DIFFICULTIES:
                    count = spec.puzzles.get(size, {}).get(difficulty, 0)
                    if count > 0:
                        sections.append((size, difficulty, count, rows, cols))

            if not sections:
                result.error = "No puzzles configured for this book."
                results.append(result)
                continue

            puzzle_sections = []
            solution_sections = []
            start_index = 0
            book_warnings = []

            for size, difficulty, count, rows, cols in sections:
                section_label = f"{size}x{size} {difficulty}"
                s = spec_for_size(size)

                def _warn_cb(index, target, actual, reason=None, _label=section_label):
                    book_warnings.append((_label, index, target, actual, reason))

                puzzles, solutions = generate_puzzles(
                    count=count,
                    spec=s,
                    difficulty=difficulty,
                    rng=rng,
                    warn_cb=_warn_cb,
                )
                puzzle_sections.append({
                    "title": section_label,
                    "spec": s,
                    "layout": (rows, cols),
                    "items": puzzles,
                    "start_index": start_index,
                })
                solution_sections.append({
                    "title": f"{section_label} Solutions",
                    "spec": s,
                    "layout": (rows, cols),
                    "items": solutions,
                    "start_index": start_index,
                })
                start_index += count

            puzzle_pages = sum(
                _pages_needed(count, rows, cols)
                for _, _, count, rows, cols in sections
            )
            solution_pages = puzzle_pages
            raw_total = puzzle_pages + solution_pages
            even_pages = compute_even_page_count(raw_total)
            result.page_count = even_pages

            margins = build_margin_spec_no_bleed(
                page_count_even=even_pages,
                outside_top_bottom_in=spec.margin_in,
                extra_gutter_in=spec.extra_gutter_in,
            )

            result.interior_pdf = build_interior_pdf(
                puzzle_sections=puzzle_sections,
                solution_sections=solution_sections,
                trim_size=(spec.trim_w, spec.trim_h),
                margin_in=spec.margin_in,
                inside_margin_in=margins.inside_in,
                include_page_numbers=spec.include_page_numbers,
                force_even_pages=True,
            )

            if spec.include_cover:
                result.cover_pdf = build_cover_pdf(
                    trim_size=(spec.trim_w, spec.trim_h),
                    page_count=even_pages,
                    bleed_in=spec.bleed_in,
                    spine_in=spec.spine_in,
                    safe_in=spec.safe_in,
                    title=spec.cover_title,
                    subtitle=spec.cover_subtitle,
                    author=spec.cover_author,
                    back_text=spec.cover_back_text,
                )

            result.warnings = book_warnings

        except Exception as exc:  # pylint: disable=broad-except
            result.error = str(exc)

        results.append(result)

    if progress_cb:
        progress_cb(total, total, "Done")

    return results


def create_batch_zip(results: list[BatchResult]) -> BytesIO:
    """Package all generated PDFs from a batch into a single ZIP file."""
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zf:
        for r in results:
            safe_name = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in r.name).strip()
            if not safe_name:
                safe_name = "book"
            if r.interior_pdf:
                zf.writestr(f"{safe_name}_interior.pdf", r.interior_pdf.getvalue())
            if r.cover_pdf:
                zf.writestr(f"{safe_name}_cover.pdf", r.cover_pdf.getvalue())
    buffer.seek(0)
    return buffer

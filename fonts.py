from __future__ import annotations

import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


FONT_REG = "AppSans"
FONT_BOLD = "AppSans-Bold"


def _candidate_font_paths() -> list[tuple[Path, Path, str]]:
    """
    Returns (regular_path, bold_path, label).
    The first existing pair will be used.
    """
    here = Path(__file__).resolve().parent
    bundled = (
        here / "assets" / "fonts" / "NotoSans-Regular.ttf",
        here / "assets" / "fonts" / "NotoSans-Bold.ttf",
        "bundled Noto Sans",
    )

    # Common Linux paths on Streamlit Community Cloud.
    dejavu = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        "system DejaVu Sans (Linux)",
    )

    # Common Windows paths for local runs.
    arial = (
        Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts" / "arialbd.ttf",
        "system Arial (Windows)",
    )

    return [bundled, dejavu, arial]


def ensure_fonts_registered() -> str:
    """
    Registers TTF fonts so they are embedded in the PDF.
    Returns a label describing which font pair was selected.
    """
    if FONT_REG in pdfmetrics.getRegisteredFontNames() and FONT_BOLD in pdfmetrics.getRegisteredFontNames():
        return "already registered"

    for reg_path, bold_path, label in _candidate_font_paths():
        if reg_path.exists() and bold_path.exists():
            pdfmetrics.registerFont(TTFont(FONT_REG, str(reg_path)))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))
            return label

    raise FileNotFoundError(
        "No embeddable TTF fonts found. Add Noto Sans files at "
        "`assets/fonts/NotoSans-Regular.ttf` and `assets/fonts/NotoSans-Bold.ttf`."
    )


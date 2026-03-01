# Sudoku Book Generator (Streamlit) v2.0

Professional, KDP-ready Sudoku puzzle book creator for Amazon Kindle Direct Publishing.
Generate print-ready interior and cover PDFs directly from your browser.

## Features

### Core
- Puzzle sizes: 6×6, 9×9, 16×16
- Difficulty levels: Easy, Medium, Hard, Expert
- Per-size/per-difficulty puzzle counts and puzzles-per-page control
- Unique-solution puzzle generation (backtracking solver with budget limits)
- KDP preset trim sizes (16 standard sizes)
- Interior PDF with puzzles + solutions (vector, print-ready)
- Cover PDF with bleed/spine/safe margin guides

### New in v2.0
- **Multi-tab UI**: Quick Generate wizard, Advanced Settings, Batch Processing, Project Manager
- **Quick Generate**: 3-step wizard (Puzzle Mix → Book Size → Cover & Generate)
- **Advanced Settings**: Full control over all parameters including PDF metadata
- **Batch Processing**: Define and generate multiple books at once, download as ZIP
- **Project Manager**: Save/load configurations as JSON, apply quick templates
- **Quick Templates**: Kids Puzzles, Adult Easy, Adult Hard, Mixed Difficulty, 16×16 Challenge
- **KDP Compliance Checklist**: Visual pass/fail status for each KDP requirement
- **Cost Estimator**: Rough KDP B&W printing cost estimate
- **In-app help**: FAQ, troubleshooting, KDP resource links
- **Professional styling**: Custom CSS, branded header, step indicators, metric cards

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Module Structure

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit application (multi-tab UI) |
| `ui_components.py` | Reusable UI building blocks |
| `config_manager.py` | Configuration save/load and quick templates |
| `validators.py` | Enhanced KDP preflight validation |
| `styles.py` | Custom CSS and Streamlit theme |
| `batch_processor.py` | Batch book generation logic |
| `pdf_utils.py` | Interior PDF generation (ReportLab) |
| `cover.py` | Cover PDF generation (ReportLab) |
| `sudoku.py` | Puzzle generation and solver |
| `kdp_specs.py` | KDP margin/page count specifications |
| `fonts.py` | Font registration for PDF embedding |

## Configuration Files (JSON)

Export your current settings from the **Project Manager** tab. The JSON file can be:
- Re-imported to restore settings
- Shared with collaborators
- Used as a starting point for a new project

## KDP Notes

- Enter spine width manually; KDP formulas vary by paper type and region.
  - White 60# paper: `page_count × 0.002252 in`
  - Cream 60# paper: `page_count × 0.0025 in`
- Always validate PDFs against current KDP specifications before publishing.
- The cost estimate in-app is approximate; use the [KDP Royalty Calculator](https://kdp.amazon.com/en_US/help/topic/G200645550) for accurate figures.

## Font Embedding

For best KDP results, add:
- `assets/fonts/NotoSans-Regular.ttf`
- `assets/fonts/NotoSans-Bold.ttf`

If missing, the app falls back to system fonts (DejaVu Sans on Linux, Arial on Windows).

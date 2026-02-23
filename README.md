# Sudoku Book Generator (Streamlit)

Generate print-ready Sudoku puzzle books for Amazon KDP with puzzles, solutions, and a full wrap cover PDF.

## Features
- Sizes: 6x6, 9x9, 16x16
- Difficulty: Easy, Medium, Hard, Expert
- Per-size/per-difficulty puzzle counts
- Puzzles-per-page per size
- Unique-solution puzzle generation
- KDP preset trim sizes
- Interior PDF with puzzles + solutions
- Cover PDF with bleed/spine/safe guides

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Enter the spine width manually; KDP formulas vary by paper type and region.
- Always validate PDFs against current KDP specs before publishing.

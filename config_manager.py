"""Configuration save/load management for Sudoku Book Generator projects."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "version": "1.0",
    "puzzle_settings": {
        "seed": "",
        "puzzles": {
            6: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
            9: {"Easy": 10, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
            16: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 1},
        },
    },
    "book_settings": {
        "trim_label": "6 x 9 in",
        "margin_in": 0.5,
        "extra_gutter_in": 0.0,
        "include_page_numbers": True,
    },
    "cover_settings": {
        "include_cover": True,
        "title": "Sudoku Puzzle Book",
        "subtitle": "Brain-Teasing Puzzles",
        "author": "Your Name",
        "back_text": (
            "Enjoy hours of entertainment with a curated set of Sudoku puzzles. "
            "Perfect for travel, relaxation, and daily brain training."
        ),
        "bleed_in": 0.125,
        "spine_in": 0.5,
        "safe_in": 0.25,
    },
    "pdf_metadata": {
        "title": "",
        "author": "",
        "subject": "Sudoku Puzzle Book",
        "keywords": "sudoku, puzzle, brain training",
    },
}

QUICK_TEMPLATES: dict[str, dict[str, Any]] = {
    "Kids Puzzles (6x6 Easy)": {
        "puzzle_settings": {
            "seed": "",
            "puzzles": {
                6: {"Easy": 50, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
                9: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
                16: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 1},
            },
        },
        "book_settings": {
            "trim_label": "8.5 x 8.5 in",
            "margin_in": 0.5,
            "extra_gutter_in": 0.0,
            "include_page_numbers": True,
        },
        "cover_settings": {
            "include_cover": True,
            "title": "Kids Sudoku",
            "subtitle": "Fun 6x6 Puzzles for Children",
            "author": "Your Name",
            "back_text": "Enjoy these fun and easy 6x6 Sudoku puzzles designed for young minds!",
            "bleed_in": 0.125,
            "spine_in": 0.5,
            "safe_in": 0.25,
        },
    },
    "Adult Easy (9x9)": {
        "puzzle_settings": {
            "seed": "",
            "puzzles": {
                6: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
                9: {"Easy": 100, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
                16: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 1},
            },
        },
        "book_settings": {
            "trim_label": "6 x 9 in",
            "margin_in": 0.5,
            "extra_gutter_in": 0.0,
            "include_page_numbers": True,
        },
        "cover_settings": {
            "include_cover": True,
            "title": "Easy Sudoku",
            "subtitle": "100 Relaxing Puzzles",
            "author": "Your Name",
            "back_text": "100 easy Sudoku puzzles to relax and unwind.",
            "bleed_in": 0.125,
            "spine_in": 0.5,
            "safe_in": 0.25,
        },
    },
    "Adult Hard (9x9)": {
        "puzzle_settings": {
            "seed": "",
            "puzzles": {
                6: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
                9: {"Easy": 0, "Medium": 0, "Hard": 100, "Expert": 0, "per_page": 4},
                16: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 1},
            },
        },
        "book_settings": {
            "trim_label": "6 x 9 in",
            "margin_in": 0.5,
            "extra_gutter_in": 0.0,
            "include_page_numbers": True,
        },
        "cover_settings": {
            "include_cover": True,
            "title": "Hard Sudoku",
            "subtitle": "100 Challenging Puzzles",
            "author": "Your Name",
            "back_text": "100 hard Sudoku puzzles to challenge even experienced solvers.",
            "bleed_in": 0.125,
            "spine_in": 0.5,
            "safe_in": 0.25,
        },
    },
    "Mixed Difficulty Book": {
        "puzzle_settings": {
            "seed": "",
            "puzzles": {
                6: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
                9: {"Easy": 30, "Medium": 30, "Hard": 30, "Expert": 10, "per_page": 4},
                16: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 1},
            },
        },
        "book_settings": {
            "trim_label": "6 x 9 in",
            "margin_in": 0.5,
            "extra_gutter_in": 0.0,
            "include_page_numbers": True,
        },
        "cover_settings": {
            "include_cover": True,
            "title": "Complete Sudoku Collection",
            "subtitle": "Easy to Expert Puzzles",
            "author": "Your Name",
            "back_text": "A mix of Easy, Medium, Hard and Expert Sudoku puzzles for all skill levels.",
            "bleed_in": 0.125,
            "spine_in": 0.5,
            "safe_in": 0.25,
        },
    },
    "16x16 Challenge Book": {
        "puzzle_settings": {
            "seed": "",
            "puzzles": {
                6: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
                9: {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "per_page": 4},
                16: {"Easy": 20, "Medium": 20, "Hard": 10, "Expert": 0, "per_page": 1},
            },
        },
        "book_settings": {
            "trim_label": "8.5 x 11 in",
            "margin_in": 0.5,
            "extra_gutter_in": 0.0,
            "include_page_numbers": True,
        },
        "cover_settings": {
            "include_cover": True,
            "title": "16x16 Sudoku Mega Challenge",
            "subtitle": "Super-Size Puzzles",
            "author": "Your Name",
            "back_text": "50 mega-size 16x16 Sudoku puzzles for advanced solvers.",
            "bleed_in": 0.125,
            "spine_in": 0.5,
            "safe_in": 0.25,
        },
    },
}


def config_to_json(config: dict[str, Any]) -> str:
    """Serialize configuration to a JSON string."""
    config["saved_at"] = datetime.utcnow().isoformat() + "Z"
    return json.dumps(config, indent=2)


def config_from_json(json_str: str) -> dict[str, Any]:
    """Deserialize configuration from a JSON string. Returns validated config."""
    data = json.loads(json_str)
    return _merge_with_defaults(data)


def _merge_with_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """Merge loaded config with defaults to fill any missing keys."""
    import copy
    result = copy.deepcopy(DEFAULT_CONFIG)

    def deep_update(base: dict, updates: dict) -> dict:
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                deep_update(base[key], value)
            else:
                base[key] = value
        return base

    return deep_update(result, config)


def apply_template(template_name: str) -> dict[str, Any]:
    """Return a config dict based on a named quick template."""
    template = QUICK_TEMPLATES.get(template_name)
    if template is None:
        return dict(DEFAULT_CONFIG)
    return _merge_with_defaults(template)


def get_template_names() -> list[str]:
    """Return list of available template names."""
    return list(QUICK_TEMPLATES.keys())

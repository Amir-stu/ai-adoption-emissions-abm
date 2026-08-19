"""
Repository paths.

Output locations are resolved from the location of this file, not from the
working directory, so every script writes to the same place whether it is run
from the repository root, from `src/`, or from anywhere else.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"


def results(filename: str) -> Path:
    """Path of an output table, creating `results/` if a fresh clone lacks it."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR / filename


def figures(filename: str) -> Path:
    """Path of an output figure, creating `figures/` if a fresh clone lacks it."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIGURES_DIR / filename

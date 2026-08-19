"""Regenerate every thesis exhibit, in dependency order.

    python run_all.py

Can be run from anywhere: each script resolves its own output location through
src/paths.py. Output lands in results/ and figures/.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
RESULTS = ROOT / "results"

# (script, what it produces) -- figure_breakeven.py reads the values that
# breakeven.py solves, so it runs after it.
STEPS = [
    ("threshold.py",            "Table 4.1  critical grid intensity G*"),
    ("results_tables.py",       "Tables 6.1, 6.2  sector, rebound, country x policy"),
    ("breakeven.py",            "Tables 6.3, 6.4  break-even values and g sweep"),
    ("figures.py",              "Figure 5.1  adoption diffusion"),
    ("figure_breakeven.py",     "Figure 6.1  break-even analysis"),
    ("figure_model_diagram.py", "model diagram  (documentation, not a thesis figure)"),
]


def run(script: str, label: str) -> None:
    print("\n=== %s  (%s) ===" % (script, label), flush=True)
    started = time.time()
    completed = subprocess.run([sys.executable, str(SRC / script)])
    if completed.returncode != 0:
        raise SystemExit("%s failed with exit code %d" % (script, completed.returncode))
    print("--- %s done in %.1fs" % (script, time.time() - started), flush=True)


def capture_uncertainty() -> None:
    """uncertainty.py reports to stdout; save that report as the Table 6.5 file."""
    print("\n=== uncertainty.py  (Table 6.5  uncertainty decomposition) ===", flush=True)
    started = time.time()
    completed = subprocess.run([sys.executable, str(SRC / "uncertainty.py")],
                               capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr or "")
        raise SystemExit("uncertainty.py failed with exit code %d" % completed.returncode)

    print(completed.stdout, end="")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "table6_5_uncertainty.txt").write_text(completed.stdout, encoding="utf-8")
    print("--- uncertainty.py done in %.1fs" % (time.time() - started), flush=True)


def main() -> None:
    total = time.time()
    for script, label in STEPS:
        run(script, label)
    capture_uncertainty()
    print("\nAll exhibits regenerated in %.1fs. See results/ and figures/."
          % (time.time() - total))


if __name__ == "__main__":
    main()

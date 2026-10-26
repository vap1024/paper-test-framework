#!/usr/bin/env python3
"""Run the synthetic demo end to end: verify the freeze, score, report.

Usage:  python src/run_demo.py [--out report.md]
Writes the report to stdout, or to --out when given. Exit code 1 when
the frozen-rules hash does not verify (the rules were edited after the
freeze -- start a new experiment version instead of reusing this one).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper_test import load_experiment, load_journal, render_report, verify_frozen  # noqa: E402


def main(argv: list[str]) -> int:
    experiment = load_experiment(ROOT / "examples" / "demo_experiment.json")
    if not verify_frozen(experiment):
        print("ERROR: frozen_hash mismatch -- rules changed after freeze.", file=sys.stderr)
        return 1
    positions = load_journal(ROOT / "examples" / "demo_journal.csv")
    report = render_report(experiment, positions)
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        out.write_text(report, encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

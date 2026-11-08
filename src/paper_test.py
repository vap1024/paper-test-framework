"""Core of paper-test-framework: frozen rules, journal parsing, honest verdicts.

Standard library only. No network access. All data is whatever journal
*you* feed it -- the bundled example journal is entirely synthetic.

The idea, in one paragraph: write the rules of a paper (no-money) test
down *before* it starts, freeze them with a hash, run every compared
source through exactly the same mechanics, and let a PASS bar that was
also written in advance -- not invented after seeing the results --
decide the verdict.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
from pathlib import Path

REQUIRED_EXPERIMENT_FIELDS = ("name", "hypothesis", "baskets", "bar")
REQUIRED_BAR_FIELDS = ("min_closed", "min_mean_pct")


# ---------------------------------------------------------------- freeze --

def canonical_config(config: dict) -> str:
    """Stable JSON rendering of a config without its frozen_hash field."""
    payload = {k: v for k, v in config.items() if k != "frozen_hash"}
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def freeze_hash(config: dict) -> str:
    """SHA-256 of the canonical config. Any later edit changes the hash."""
    return hashlib.sha256(canonical_config(config).encode("utf-8")).hexdigest()


def verify_frozen(config: dict) -> bool:
    """True when the stored frozen_hash still matches the current rules."""
    stored = config.get("frozen_hash")
    return bool(stored) and stored == freeze_hash(config)


def load_experiment(path: str | Path) -> dict:
    """Load and validate an experiment config; raise ValueError if incomplete."""
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("experiment config must be a JSON object")
    missing = [f for f in REQUIRED_EXPERIMENT_FIELDS if f not in config]
    if missing:
        raise ValueError(f"experiment config is missing fields: {', '.join(missing)}")
    if not isinstance(config["bar"], dict):
        raise ValueError("experiment bar must be an object")
    bar_missing = [f for f in REQUIRED_BAR_FIELDS if f not in config["bar"]]
    if bar_missing:
        raise ValueError(f"experiment bar is missing fields: {', '.join(bar_missing)}")
    if not isinstance(config["name"], str) or not config["name"].strip():
        raise ValueError("experiment name must be a non-empty string")
    if not isinstance(config["hypothesis"], str) or not config["hypothesis"].strip():
        raise ValueError("experiment hypothesis must be a non-empty string")

    bar = config["bar"]
    min_closed = bar["min_closed"]
    if isinstance(min_closed, bool) or not isinstance(min_closed, int) or min_closed < 1:
        raise ValueError("bar.min_closed must be an integer greater than or equal to 1")
    min_mean_pct = bar["min_mean_pct"]
    finite_mean = isinstance(min_mean_pct, int) and not isinstance(min_mean_pct, bool)
    if isinstance(min_mean_pct, float):
        finite_mean = math.isfinite(min_mean_pct)
    if (isinstance(min_mean_pct, bool) or not isinstance(min_mean_pct, (int, float))
            or not finite_mean):
        raise ValueError("bar.min_mean_pct must be a finite number")
    if ("require_without_top1_positive" in bar
            and not isinstance(bar["require_without_top1_positive"], bool)):
        raise ValueError("bar.require_without_top1_positive must be a boolean")

    baskets = config["baskets"]
    if not isinstance(baskets, list):
        raise ValueError("baskets must be a list")
    if not baskets:
        raise ValueError("baskets must contain at least one entry")
    if any(not isinstance(basket, str) or not basket.strip() for basket in baskets):
        raise ValueError("baskets entries must be non-empty strings")
    if len(set(baskets)) != len(baskets):
        raise ValueError("baskets must not contain duplicates")
    return config


# --------------------------------------------------------------- journal --

def parse_journal(text: str) -> list[dict]:
    """Parse a journal CSV with columns: basket, asset, net_pct.

    Extra columns are kept as strings. Rows with a non-numeric net_pct
    raise ValueError -- a silent skip would quietly change the sample.
    Rows without a basket raise ValueError for the same reason: the
    report scores positions per basket, so a basketless row would be
    accepted here and then silently dropped from every verdict.
    """
    rows: list[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or "net_pct" not in reader.fieldnames:
        raise ValueError("journal CSV must have a net_pct column")
    if "basket" not in reader.fieldnames:
        raise ValueError("journal CSV must have a basket column")
    for line_no, row in enumerate(reader, start=2):
        basket = (row.get("basket") or "").strip()
        if not basket:
            raise ValueError(f"journal line {line_no}: basket is empty")
        try:
            net = float(row["net_pct"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"journal line {line_no}: net_pct is not a number") from exc
        parsed = {k: v for k, v in row.items() if k is not None}
        parsed["basket"] = basket
        parsed["net_pct"] = net
        rows.append(parsed)
    return rows


def load_journal(path: str | Path) -> list[dict]:
    return parse_journal(Path(path).read_text(encoding="utf-8"))


# ----------------------------------------------------------------- stats --

def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (pct in 0..100)."""
    if not 0.0 <= pct <= 100.0:
        raise ValueError(f"percentile pct must be within 0..100, got {pct}")
    if not values:
        raise ValueError("percentile of an empty sample")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return ordered[low] + frac * (ordered[high] - ordered[low])


def stats_of(positions: list[dict]) -> dict | None:
    """Summary statistics for one basket's closed paper positions."""
    if not positions:
        return None
    nets = [float(p["net_pct"]) for p in positions]
    total = sum(nets)
    without_top1 = total - max(nets) if len(nets) > 1 else 0.0
    return {
        "n": len(nets),
        "mean_pct": round(statistics.mean(nets), 3),
        "median_pct": round(statistics.median(nets), 3),
        "p10_pct": round(percentile(nets, 10), 3),
        "p90_pct": round(percentile(nets, 90), 3),
        "winrate_pct": round(100.0 * sum(1 for x in nets if x > 0) / len(nets), 1),
        "total_pct": round(total, 3),
        "without_top1_total_pct": round(without_top1, 3),
    }


# --------------------------------------------------------------- verdict --

def verdict_for(positions: list[dict], bar: dict) -> dict:
    """Apply a pre-registered bar. Verdicts:

    INSUFFICIENT_DATA -- fewer closed positions than the bar requires.
    PASS              -- mean clears the bar AND the result does not rest
                         on the single best position alone.
    NOISE             -- mean clears the bar, but removing the best
                         position makes the total non-positive.
    BELOW_BAR         -- enough data, mean does not clear the bar
                         (this includes every non-positive mean).
    """
    stats = stats_of(positions)
    if stats is None or stats["n"] < int(bar["min_closed"]):
        return {"verdict": "INSUFFICIENT_DATA", "stats": stats,
                "reasons": [f"closed positions below the pre-registered minimum "
                            f"({0 if stats is None else stats['n']} < {bar['min_closed']})"]}
    reasons = []
    clears = stats["mean_pct"] >= float(bar["min_mean_pct"])
    reasons.append(f"mean {stats['mean_pct']:+.3f}% vs bar {float(bar['min_mean_pct']):+.3f}%")
    if not clears:
        return {"verdict": "BELOW_BAR", "stats": stats, "reasons": reasons}
    if bar.get("require_without_top1_positive", True) and stats["without_top1_total_pct"] <= 0:
        reasons.append(f"total without the best position is "
                       f"{stats['without_top1_total_pct']:+.3f}% -- result rests on one ticket")
        return {"verdict": "NOISE", "stats": stats, "reasons": reasons}
    reasons.append(f"total without the best position stays positive "
                   f"({stats['without_top1_total_pct']:+.3f}%)")
    return {"verdict": "PASS", "stats": stats, "reasons": reasons}


# ---------------------------------------------------------------- report --

def render_report(experiment: dict, positions: list[dict]) -> str:
    """Markdown report: one section per basket, each with its verdict."""
    lines = [f"# Paper test report: {experiment['name']}", "",
             f"Hypothesis: {experiment['hypothesis']}", "",
             f"Rules frozen: {'yes, hash verified' if verify_frozen(experiment) else 'NO -- hash mismatch or missing'}",
             ""]
    for basket in experiment["baskets"]:
        own = [p for p in positions if p.get("basket") == basket]
        result = verdict_for(own, experiment["bar"])
        lines += [f"## Basket `{basket}` -- {result['verdict']}", ""]
        if result["stats"]:
            s = result["stats"]
            lines += [f"- closed: {s['n']} | mean {s['mean_pct']:+.3f}% | median {s['median_pct']:+.3f}% "
                      f"| p10 {s['p10_pct']:+.3f}% | p90 {s['p90_pct']:+.3f}%",
                      f"- winrate {s['winrate_pct']}% | total {s['total_pct']:+.3f}% "
                      f"| total without best position {s['without_top1_total_pct']:+.3f}%"]
        for reason in result["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")
    lines += ["_Synthetic demo data only. A verdict describes this sample "
              "under these frozen rules -- nothing else._", ""]
    return "\n".join(lines)

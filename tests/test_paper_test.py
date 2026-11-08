"""Tests for frozen rules, statistics and verdict logic."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import run_demo  # noqa: E402
from paper_test import (  # noqa: E402
    freeze_hash,
    load_experiment,
    load_journal,
    parse_journal,
    percentile,
    render_report,
    stats_of,
    verdict_for,
    verify_frozen,
)

BAR = {"min_closed": 3, "min_mean_pct": 1.0, "require_without_top1_positive": True}


def positions(*nets: float, basket: str = "b") -> list[dict]:
    return [{"basket": basket, "asset": f"SYN-{i}", "net_pct": n} for i, n in enumerate(nets)]


class FreezeTests(unittest.TestCase):
    def test_demo_config_verifies(self) -> None:
        config = load_experiment(ROOT / "examples" / "demo_experiment.json")
        self.assertTrue(verify_frozen(config))

    def test_any_rule_edit_breaks_the_freeze(self) -> None:
        config = load_experiment(ROOT / "examples" / "demo_experiment.json")
        tampered = copy.deepcopy(config)
        tampered["bar"]["min_mean_pct"] = 0.1  # quietly lowering the bar afterwards
        self.assertFalse(verify_frozen(tampered))
        self.assertNotEqual(freeze_hash(tampered), tampered["frozen_hash"])

    def test_missing_fields_are_rejected(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text(json.dumps({"name": "x"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_experiment(path)


class LoadExperimentValidationTests(unittest.TestCase):
    def assert_invalid_config(self, mutate) -> None:
        import json
        import tempfile

        config = json.loads((ROOT / "examples" / "demo_experiment.json").read_text(encoding="utf-8"))
        mutate(config)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text(json.dumps(config, allow_nan=True), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_experiment(path)

    def test_min_closed_must_be_a_positive_integer(self) -> None:
        for value in (0, -3, "two", 2.5, True):
            with self.subTest(value=value):
                self.assert_invalid_config(lambda config: config["bar"].__setitem__("min_closed", value))

    def test_min_mean_pct_must_be_finite_number(self) -> None:
        for value in ("high", None, float("nan"), float("inf")):
            with self.subTest(value=value):
                self.assert_invalid_config(lambda config: config["bar"].__setitem__("min_mean_pct", value))

    def test_bar_must_be_an_object(self) -> None:
        for value in (None, "not-a-dict", []):
            with self.subTest(value=value):
                self.assert_invalid_config(lambda config: config.__setitem__("bar", value))

    def test_baskets_must_be_a_unique_list_of_non_empty_strings(self) -> None:
        for value in ("ABC", [], [""], ["A", "A"], [42]):
            with self.subTest(value=value):
                self.assert_invalid_config(lambda config: config.__setitem__("baskets", value))

    def test_config_root_must_be_an_object(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_experiment(path)

    def test_require_without_top1_positive_must_be_boolean(self) -> None:
        self.assert_invalid_config(
            lambda config: config["bar"].__setitem__("require_without_top1_positive", "yes")
        )

    def test_name_must_be_non_empty(self) -> None:
        self.assert_invalid_config(lambda config: config.__setitem__("name", ""))

    def test_header_only_journal_marks_every_basket_insufficient(self) -> None:
        config = load_experiment(ROOT / "examples" / "demo_experiment.json")
        rows = parse_journal("basket,asset,net_pct\n")
        self.assertEqual(rows, [])
        report = render_report(config, rows)
        for basket in config["baskets"]:
            with self.subTest(basket=basket):
                self.assertIn(f"## Basket `{basket}` -- INSUFFICIENT_DATA", report)


class JournalTests(unittest.TestCase):
    def test_demo_journal_loads(self) -> None:
        rows = load_journal(ROOT / "examples" / "demo_journal.csv")
        self.assertEqual(len(rows), 24)
        self.assertEqual({r["basket"] for r in rows}, {"source-a", "source-b"})

    def test_non_numeric_net_is_an_error_not_a_skip(self) -> None:
        with self.assertRaises(ValueError):
            parse_journal("basket,asset,net_pct\nb,SYN-1,soon\n")

    def test_missing_basket_column_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            parse_journal("asset,net_pct\nSYN-1,5.0\n")

    def test_empty_basket_is_an_error_not_a_silent_drop(self) -> None:
        # A basketless row parses fine but matches no basket in the
        # report, so it would vanish from every verdict unnoticed.
        with self.assertRaises(ValueError):
            parse_journal("basket,asset,net_pct\n,SYN-1,5.0\n")


class StatsTests(unittest.TestCase):
    def test_stats_and_percentiles(self) -> None:
        stats = stats_of(positions(1.0, 2.0, 3.0, 4.0))
        self.assertEqual(stats["n"], 4)
        self.assertEqual(stats["mean_pct"], 2.5)
        self.assertEqual(stats["median_pct"], 2.5)
        self.assertEqual(stats["winrate_pct"], 100.0)
        self.assertEqual(stats["without_top1_total_pct"], 6.0)
        self.assertAlmostEqual(percentile([1.0, 2.0, 3.0, 4.0], 10), 1.3)

    def test_empty_sample_has_no_stats(self) -> None:
        self.assertIsNone(stats_of([]))

    def test_percentile_bounds_return_the_extremes(self) -> None:
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 0), 1.0)
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 100), 4.0)

    def test_percentile_out_of_range_is_an_error(self) -> None:
        # Above 100 this used to crash with IndexError; below 0 it
        # silently extrapolated to a value outside the sample.
        for bad in (-10, 100.5, 150):
            with self.assertRaises(ValueError):
                percentile([1.0, 2.0, 3.0, 4.0], bad)


class RunDemoTests(unittest.TestCase):
    def test_out_without_a_path_is_a_clean_error(self) -> None:
        self.assertEqual(run_demo.main(["--out"]), 2)


class VerdictTests(unittest.TestCase):
    def test_pass(self) -> None:
        result = verdict_for(positions(2.0, 3.0, 4.0, -0.5), BAR)
        self.assertEqual(result["verdict"], "PASS")

    def test_noise_when_one_ticket_carries_the_result(self) -> None:
        result = verdict_for(positions(30.0, -2.0, -2.0, -2.0), BAR)
        self.assertEqual(result["verdict"], "NOISE")

    def test_below_bar(self) -> None:
        result = verdict_for(positions(0.5, 0.2, -0.1, 0.4), BAR)
        self.assertEqual(result["verdict"], "BELOW_BAR")

    def test_insufficient_data(self) -> None:
        result = verdict_for(positions(9.0, 9.0), BAR)
        self.assertEqual(result["verdict"], "INSUFFICIENT_DATA")


class ReportTests(unittest.TestCase):
    def test_demo_report_shows_one_pass_and_one_noise(self) -> None:
        config = load_experiment(ROOT / "examples" / "demo_experiment.json")
        rows = load_journal(ROOT / "examples" / "demo_journal.csv")
        report = render_report(config, rows)
        self.assertIn("source-a` -- PASS", report)
        self.assertIn("source-b` -- NOISE", report)
        self.assertIn("hash verified", report)


if __name__ == "__main__":
    unittest.main()

# Changelog

## Unreleased

### Fixed

- `percentile()` now rejects a `pct` outside 0..100 with `ValueError`.
  Above 100 it used to crash with `IndexError`; below 0 it silently
  extrapolated to a value outside the sample.
- `parse_journal()` now requires a `basket` column and a non-empty
  basket on every row. Basketless rows were accepted and then silently
  dropped from every per-basket verdict -- the same quiet sample change
  the non-numeric `net_pct` check already guards against.
- `run_demo.py --out` without a path now exits with a usage error
  (exit code 2) instead of an `IndexError` traceback.

### Added

- GitHub Actions workflow: unit tests, a demo smoke run and a check
  that the committed `examples/demo_report.md` matches a fresh demo
  run, on Python 3.11 and 3.12.
- Tests for the three fixes above (17 tests total).

## 0.1.0 - 2026-10-26

- Initial public package: frozen-rules experiment configs (SHA-256
  freeze hash), journal parsing, per-basket statistics and honest
  PASS / NOISE / BELOW_BAR / INSUFFICIENT_DATA verdicts, synthetic
  two-basket demo.

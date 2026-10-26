# paper-test-framework

A small standard-library framework for running **paper tests** — tests of a
trading or signal idea on paper, with no real money — without fooling
yourself afterwards. It runs locally and makes no network requests.

The failure mode it exists to prevent is ordinary: a test starts loosely,
the rules quietly drift while it runs, and at the end the bar is drawn
wherever the result happened to land. This framework makes that drift
visible instead of comfortable.

## The method

1. **Write the rules before the start.** Signal definition, entry, exit,
   paper size, cost model, end condition — see `RULES-template.md`.
2. **Freeze them.** The experiment config carries a SHA-256
   `frozen_hash` of itself. Any later edit — including quietly lowering
   the PASS bar — breaks the hash, and the demo runner refuses to score
   a test whose rules no longer verify. A real rule change is allowed
   exactly one way: a new version, a new cohort, counted from zero.
3. **Identical mechanics for everything compared.** When two signal
   sources ("baskets") are compared, they share entry, exit, sizing and
   cost rules. A comparison where one side gets friendlier mechanics
   proves nothing.
4. **Pre-register the PASS bar.** Minimum sample size and minimum mean
   result are fixed while nobody knows the outcome.
5. **Check concentration.** Even a passing mean is only `NOISE` when the
   whole result rests on the single best position: the total without
   that position must stay positive for a `PASS`.
6. **Report mean, median and the tails together** (p10/p90, winrate) —
   a mean carried by a few outliers and a typical result are different
   claims, and an honest report shows both.

## Verdicts

| Verdict | Meaning |
|---|---|
| `PASS` | Enough data, mean clears the pre-registered bar, result does not rest on one ticket. |
| `NOISE` | Mean clears the bar, but removing the best position makes the total non-positive. |
| `BELOW_BAR` | Enough data, mean does not clear the bar (including any non-positive mean). |
| `INSUFFICIENT_DATA` | Fewer closed positions than the pre-registered minimum. Reported with the numbers as they are — never rounded up to a verdict. |

## Quick start

Requires Python 3.11 or newer. No dependencies.

```console
python src/run_demo.py
python src/run_demo.py --out my_report.md
```

The demo scores a fully synthetic two-basket experiment
(`examples/demo_experiment.json` + `examples/demo_journal.csv`): basket
`source-a` earns a `PASS`, basket `source-b` is exposed as `NOISE` — its
average looks fine until the one lucky ticket is removed. The generated
example output is in [`examples/demo_report.md`](examples/demo_report.md).

To start your own test: copy `RULES-template.md`, fill it in, express
the bar in an experiment JSON like the demo one, freeze it, and only
then start recording a journal CSV with columns `basket,asset,net_pct`
(one row per closed paper position).

## Failure log (honest, from real use of this method)

- A test whose rules were "clarified" mid-run produced a beautiful
  result that no frozen re-run could reproduce. The clarification *was*
  the result. Hence the hash.
- An early version compared two baskets with different price sources;
  the "winner" was simply the source with the friendlier prices. Hence
  identical mechanics, including data source.
- A strategy passed on mean while its median position lost money: the
  profit lived in a handful of tail outcomes. That can still be a real
  effect — but it must be reported as one, not as a typical result.
- Ending a test early because the interim numbers looked bad (or good)
  is another silent rule edit. If an early-stop condition exists, it
  belongs in the frozen rules.

## Limitations

- Paper execution is not real execution: unless your config models
  fees, spread and slippage, absolute returns are optimistic. A
  same-mechanics comparison between baskets stays meaningful; a claim
  about real-money returns needs the cost model.
- A `PASS` describes one sample under one frozen rule set. It is not
  evidence the effect survives a different period or market regime.
- The framework scores closed positions you give it; collecting the
  signals and prices for a live test is deliberately out of scope.

## Tests

The tests use `unittest` and are also collectable by pytest:

```console
python -m unittest discover -s tests -v
python -m pytest
```

Built with Codex, October 2026

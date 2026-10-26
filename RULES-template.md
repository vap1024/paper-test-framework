# RULES template — fill in BEFORE the test starts, then freeze

> Copy this file into your experiment folder, fill every bracket,
> compute the frozen hash (see README), and never edit the filled
> version again. A rule change means a new version and a new cohort
> counted from zero — not a quiet edit of the running test.

- **Name:** [short experiment name]
- **Hypothesis:** [one sentence: what should be true if the idea works]
- **Frozen on:** [date, before the first counted signal]
- **Baskets compared:** [the sources being compared, if any; identical
  mechanics for every basket is the whole point]
- **Signal definition:** [exactly what counts as a signal; what is
  excluded, and why]
- **Entry:** [which price, how long you wait for one, what happens when
  no price is available]
- **Exit:** [the full schedule — partial exits, time exit, dead-asset
  rule — with no discretion left to the operator]
- **Paper size:** [fixed amount per signal]
- **Costs:** [modelled or not; if not, say so and say what that does to
  absolute vs relative results]
- **PASS bar (pre-registered):**
  - minimum closed positions: [n]
  - minimum mean net result: [value]
  - concentration check: result without the single best position must
    stay positive, otherwise the verdict is NOISE, not PASS: [yes/no]
- **Early stop:** [the condition, if any, under which the test dies
  before reaching the full sample — written now, not improvised later]
- **End condition:** [sample size, calendar cap, or both]
- **Reporting cadence:** [how often summaries are produced; no
  per-event noise in between]
- **Known limitations:** [what this test cannot prove even if it passes]

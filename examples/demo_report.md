# Paper test report: synthetic-demo-two-sources

Hypothesis: Demo only: source-a produces steadier paper returns than source-b under identical mechanics.

Rules frozen: yes, hash verified

## Basket `source-a` -- PASS

- closed: 12 | mean +2.000% | median +2.500% | p10 -1.550% | p90 +5.280%
- winrate 66.7% | total +24.000% | total without best position +17.500%
- mean +2.000% vs bar +1.500%
- total without the best position stays positive (+17.500%)

## Basket `source-b` -- NOISE

- closed: 12 | mean +1.500% | median -2.000% | p10 -2.190% | p90 -1.710%
- winrate 8.3% | total +18.000% | total without best position -22.000%
- mean +1.500% vs bar +1.500%
- total without the best position is -22.000% -- result rests on one ticket

_Synthetic demo data only. A verdict describes this sample under these frozen rules -- nothing else._

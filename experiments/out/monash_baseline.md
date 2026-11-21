# Monash Car Parts: reproduced baseline and intermittent-demand models

2674 real monthly car-parts demand series, last 12 months held out, mean MASE (12-month seasonal-naive scaling). 16 series have an undefined MASE (flat history) and are skipped.

| Model | MASE, rounded to whole units (Monash setup) | Published (Monash) | MASE, not rounded |
|---|---|---|---|
| Zero forecast | 0.746 |  | 0.746 |
| ADIDA | 0.830 |  | 1.021 |
| IMAPA | 0.834 |  | 1.019 |
| TSB | 0.881 |  | 1.045 |
| SES (optimised alpha only) | 0.887 |  | 1.046 |
| SES (optimised alpha and start level, as in R) | 0.895 | 0.897 | 1.095 |
| HistoricAverage | 0.909 |  | 1.126 |
| CrostonOptimized | 1.071 |  | 1.330 |
| CrostonSBA | 1.129 |  | 1.361 |
| Naive | 1.137 |  | 1.137 |
| CrostonClassic | 1.160 |  | 1.395 |

Reading: forecasting zero for every part every month scores best on this metric, because three quarters of all months have no demand. So this leaderboard metric cannot be used to decide whether a store can safely lend a part; that needs a stockout-risk measure instead.

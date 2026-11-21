# StallBreaker

A re-planner for a car service shop when a part goes missing mid-repair. The car is
half dismantled on the lift, so the bay is blocked. StallBreaker decides **where the
part comes from** and **how the rest of the day is re-planned** in one optimisation,
then shows the service manager a before/after plan to approve.

Built for Tekion's Tek Qubit hackathon (use case: Service Parts Shortage Resolver Agent).
Status: working engine, benchmark and tests. No web app or dealer-system integration yet.

![Before and after a stall](experiments/out/toy_before_after.png)

## How it works

- Every repair order needs one technician with the right skill and one bay of the right
  kind for its whole duration.
- A stalled job keeps its bay but frees its technician until the part arrives.
- Each candidate source (sister store, local vendor, OEM depot) has an arrival time, a
  cost, and a risk that the giving store runs out. Unsafe sources are excluded unless a
  manager forces one.
- The source is a decision variable in the same Google OR-Tools CP-SAT model as the
  schedule, so a slower, cheaper source wins whenever the schedule cannot use a faster one.
- Goals are solved in strict order: fewest missed promise times, least lateness, lowest
  sourcing cost, fewest moved jobs. Work already in progress is never touched.
- An independent checker (`validate`) re-verifies every plan: no double-booked technician
  or bay, right skills, work resumes only after the part arrives.

The model follows the pattern of Google's flexible job-shop example
(optional intervals, exactly-one alternative, no-overlap).

## Run it

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest -q                      # 7 checks
.venv/bin/python experiments/toy.py                # 8 jobs, 3 bays, one missing part
.venv/bin/python experiments/eval.py 200           # 200 seeded stalls, six methods
.venv/bin/python experiments/monash_baseline.py    # forecasting baseline on real data
```

| File | Purpose |
|---|---|
| `shopcore.py` | CP-SAT re-planner, two baseline schedulers, plan checker, metrics |
| `shopgen.py` | Seeded generator of synthetic shop days and stalls |
| `shopviz.py` | Before/after Gantt chart |
| `experiments/` | Toy case, benchmark, forecasting baseline, and their outputs in `out/` |

## Results

### 200 seeded stalls on the simulator

12 repair orders, 4 technicians, 4 bays per day; one missing part; 4 candidate sources.
Averages per stall.

| Method | Promises missed | Late minutes | Bay blocked (min) | Jobs moved | Sourcing cost ($) | Max solve (s) |
|---|---|---|---|---|---|---|
| wait, cheapest source | 1.74 | 186.4 | 242.2 | 0.95 | 0.0 | 0.00 |
| wait, fastest source | 0.18 | 5.6 | 57.4 | 0.68 | 64.9 | 0.00 |
| rule dispatch, fastest source | 0.15 | 5.1 | 58.9 | 1.06 | 64.9 | 0.00 |
| solver, cheapest source fixed | 0.96 | 112.3 | 242.7 | 0.81 | 0.0 | 0.10 |
| solver, fastest source fixed | 0.12 | 4.2 | 59.9 | 0.53 | 64.9 | 0.09 |
| StallBreaker (joint) | 0.12 | 4.2 | 78.2 | 0.57 | 41.9 | 0.09 |

- Morning plans with a missed promise before any stall: 4 of 200.
- Joint solves proven optimal within the time cap: 200 of 200.
- Joint solver picked the fastest safe source in 136 of 200 stalls, the cheapest safe source in 12, and something in between in 52.
- Negative controls (no stall, plan must stay untouched): 200 of 200 passed.
- Every plan from every method passed the independent rule checker (validate).

Reading: picking a fast source does most of the work. Choosing source and schedule
together keeps the same number of promises as "fastest source first" while spending
about a third less on sourcing.

### Forecasting baseline on real car-parts demand

To judge whether a sister store can safely lend a part, the plan is to forecast its
demand from the Monash Car Parts dataset (2,674 real monthly series). First step:
reproduce the published baseline.

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

Simple exponential smoothing reproduces the published number (0.895 against 0.897).
A forecast of zero for every part beats every model on this metric, because three
quarters of all months have no demand. So this metric cannot decide whether lending a
part is safe; a stockout-risk measure is needed instead.

## Limits

- The shop is simulated. No public dataset of dealer repair orders, bays or multi-store
  stock exists, so these numbers compare methods; they do not predict dealer savings.
- Donor stockout risks in the toy case are invented numbers, not yet computed from data.
- Source arrival times are fixed values, not ranges.
- Instances are small (12 jobs). Solve time on a 40-job day is not measured yet.

## Next

Mock dealer-system API, nightly check of tomorrow's jobs against stock, donor risk from
the demand data, approval screen with plan diff and audit log, robustness to late parts.

## Sources

- Google OR-Tools flexible job-shop example (Apache-2.0): https://github.com/google/or-tools/blob/stable/examples/python/flexible_job_shop_sat.py
- Monash Car Parts dataset (CC BY 4.0), included in `data/`: https://zenodo.org/records/4656021
- Monash evaluation script: https://github.com/rakshitha123/TSForecasting/blob/master/experiments/fixed_horizon.R
- Godahewa et al., Monash Time Series Forecasting Archive: https://arxiv.org/abs/2105.06643

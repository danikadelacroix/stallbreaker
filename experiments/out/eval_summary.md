# StallBreaker benchmark on the simulator (200 seeded stalls)

12 repair orders, 4 technicians, 4 bays per day; one missing part per day; 4 candidate sources.
All data is synthetic. Averages per stall.

| Method | Promises missed | Late minutes | Bay blocked (min) | Jobs moved | Sourcing cost ($) | Max solve (s) |
|---|---|---|---|---|---|---|
| wait, cheapest source | 1.74 | 186.4 | 242.2 | 0.95 | 0.0 | 0.00 |
| wait, fastest source | 0.18 | 5.6 | 57.4 | 0.68 | 64.9 | 0.00 |
| rule dispatch, fastest source | 0.15 | 5.1 | 58.9 | 1.06 | 64.9 | 0.00 |
| solver, cheapest source fixed | 0.96 | 112.3 | 242.7 | 0.81 | 0.0 | 0.02 |
| solver, fastest source fixed | 0.12 | 4.2 | 59.9 | 0.53 | 64.9 | 0.02 |
| StallBreaker (joint) | 0.12 | 4.2 | 78.2 | 0.57 | 41.9 | 0.02 |
| StallBreaker (joint, may roll the car out) | 0.12 | 4.2 | 78.2 | 0.57 | 41.9 | 0.04 |

- Morning plans with a missed promise before any stall: 4 of 200.
- Joint solves proven optimal within the time cap: 200 of 200.
- Joint solver picked the fastest safe source in 136 of 200 stalls, the cheapest safe source in 12, and something in between in 52.
- Negative controls (no stall, plan must stay untouched): 200 of 200 passed.
- Every plan from every method passed the independent rule checker (validate).

- The stalled car could be made movable in 84 of 200 stalls (our assumption per job type). The engine rolled it out in 0 of those: only where that kept a promise, cut waiting or saved money.
- Over all 200 stalls, allowing a roll-out saved 0 missed promises, 0 late minutes, $0 of sourcing cost and 0 minutes of blocked bay in total.

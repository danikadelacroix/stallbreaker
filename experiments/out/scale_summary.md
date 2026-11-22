# Scale check (simulated shops, one stall per day, solver capped at 5 s)

| Jobs | Technicians | Bays | Days | Median re-plan (s) | Slowest (s) | Proven optimal | Missed promises: solver / rule dispatch |
|---|---|---|---|---|---|---|---|
| 12 | 4 | 4 | 20 | 0.01 | 0.04 | 20 of 20 | 4 / 6 |
| 24 | 7 | 7 | 20 | 0.03 | 0.04 | 20 of 20 | 8 / 10 |
| 40 | 12 | 12 | 20 | 0.05 | 0.11 | 20 of 20 | 2 / 2 |
| 60 | 18 | 18 | 20 | 0.14 | 0.49 | 20 of 20 | 0 / 0 |

The morning plan here comes from the earliest-promise dispatch rule, not the solver, so some days start with missed promises.
Every plan passed the rule checker. A plan that is not proven optimal within the cap is still valid; the engine flags it.

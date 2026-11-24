# 109 Hold the bay, or roll the car out?

**Status:** Proposed · **Owner:** unassigned · **Depends on:** 001, 004

## Why

A simple planner assumes a waiting car leaves its bay. Ours assumes it never can. A real shop
decides case by case: a car with its wheels off can be put back together enough to roll out in
20 minutes; a car with the engine out cannot move at all. Making that a decision the engine
takes covers both, and each simpler assumption becomes a special case of it.

## Rules

1. Each job type says whether a car taken apart can be made movable, and how many technician minutes that takes (`roll_out_min`), plus the minutes to set it up again (`set_up_min`). Some job types cannot be moved at all.
2. For a stall in progress the engine chooses between: hold (the bay stays blocked until the work is done, as today) and roll out (a technician spends `roll_out_min` now, the bay is free while the car waits outside, and the rest of the work plus `set_up_min` is done later in any bay of the right kind).
3. The choice is made inside the same model as the source and the schedule, under the same goal order.
4. The proposal says which was chosen and why in one sentence ("Rolling the car out frees Bay 7 for 3 h and saves 1 promise, at 35 extra technician minutes").
5. `validate` checks both cases.
6. With rolling out switched off for every job type, all current results are unchanged.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | A job type that cannot move is always held | to write |
| A2 | A designed day where rolling out saves a promise: the engine rolls out | to write |
| A3 | A designed day where rolling out saves nothing: the engine holds | to write |
| A4 | Rule 6: existing suite passes unchanged | existing suite |
| A5 | Benchmark re-run with roll-out allowed, table added to the results | `experiments/eval.py` |

## Open questions

- Roll-out minutes per job type are our assumption. Label them as such and ask a Tekion mentor for real ones.

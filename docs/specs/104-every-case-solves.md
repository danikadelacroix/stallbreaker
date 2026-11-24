# 104 Every demo case solves

**Status:** Fast version built · **Owner:** unassigned · **Depends on:** 004

## Why

A user can click any job and report any part missing. None of those clicks may fail.

## Rules

1. A check script reports every (repair order, part) pair on the demo day as missing, one at a time from a fresh reset, at the demo start time (10:30).
2. Each must return either a proposal whose options all pass `validate` within 5 seconds, or a clear 409 for a rule in 004 (for example the job is finished).
3. It never returns 500, and never "could not find a workable plan".
4. It records per pair: options returned, solve time, proven best or not, missed promises.
5. It runs on both demo days once 102 is built.
6. A fast version (a sample of 10 pairs) runs in the normal test suite; the full sweep runs on demand.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Sample of 10 pairs passes rules 2 and 3 | `test_sample_of_demo_stalls_all_solve` |
| A2 | Full sweep passes with a written summary | `experiments/every_case.py` (to write), output in `experiments/out/` |

## Out of scope

Pairs at other clock times (could be added after).

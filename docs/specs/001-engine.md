# 001 Re-planning engine

**Status:** Built · **Code:** `shopcore.py` · **Tests:** `tests/test_stallbreaker.py`

## Why

When a part goes missing, the choice of part source and the re-plan of the day depend on each
other. A fast expensive source is wasted if the schedule could have absorbed a slow free one.
The engine decides both in one model.

## Rules

**Schedule**

1. Every job gets exactly one technician who has its skill and exactly one bay of a kind it allows, for its whole duration.
2. No technician and no bay does two jobs at once.
3. A job never starts before its release time.
4. Jobs already finished or running at `now` keep their assignment.
5. Jobs listed in `pinned` keep their assignment. Periods in `blocks` make that bay unavailable.

**Stall**

6. A job stalled in progress keeps its bay from the stall until it finishes. Its technician is free while it waits.
7. Its remaining work starts no earlier than the part's arrival time, in the same bay.
8. A stalled job that has not started simply cannot start before the part arrives. It may move to another bay and technician.
9. The part source is a decision in the same model as the schedule. Exactly one source is chosen.
10. A source marked unsafe is never chosen, unless the caller forces it (`force_source` or `allow_unsafe`).

**Goals**

11. Goals are solved in strict order: a later goal never makes an earlier one worse. The order is a parameter. Goal names: `late` (missed promises), `tard` (late minutes), `cost` (sourcing cost), `moves` (jobs moved), `shift` (total start-time change), `hold` (bay blocked minutes).
12. With no stall, nothing moves.

**Trust**

13. `validate` re-checks any plan against rules 1 to 8 independently of the solver and raises on a violation.
14. The result says whether it is proven optimal (`info["proven"]`) and how long it took.
15. With `deterministic=True` the same input gives the same plan.

**Baselines** (for comparison only)

16. `right_shift`: no re-plan, everything after the stall waits.
17. `dispatch_edd`: rule-based dispatch by earliest promise time.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | The morning plan of the sample day keeps every promise | `test_morning_plan_keeps_every_promise` |
| A2 | The sample stall is repaired without a missed promise | `test_toy_stall_is_repaired_without_missing_a_promise` |
| A3 | Rule 10 | `test_unsafe_source_is_never_picked_unless_forced` |
| A4 | Rules 6 and 7 | `test_work_resumes_only_after_the_part_arrives_and_in_the_same_bay` |
| A5 | Rule 12 | `test_nothing_wrong_means_nothing_moves` |
| A6 | The solver never misses more promises than either baseline | `test_solver_never_loses_to_the_baselines_on_missed_promises` |
| A7 | Rule 15 | `test_same_stall_gives_the_same_plan` |
| A8 | Rule 8 | `test_a_job_not_yet_started_waits_for_its_part` |
| A9 | Rule 5 | `test_pinned_jobs_and_blocked_bays_are_respected` |

Benchmarks backing the README results: `experiments/eval.py` (200 stalls) and `experiments/scale.py` (12 to 60 jobs).

## Out of scope

Arrival times as ranges (a single value today), more than one stall solved at once, technician
breaks and shift ends, partial work handed between technicians.

## Open questions

- Should blocked-bay time be a default goal ahead of cost? Today it is last. Decide with the results page (101).

# 101 Results page

**Status:** Proposed · **Owner:** unassigned · **Depends on:** 001

## Why

The first question about any planner is "how do you know it is better?" The answer is the 200-stall benchmark, and it
should be one click away inside the app, not only in the README.

## Rules

1. A "Results" view in the app shows the benchmark table: the six methods from `experiments/eval.py` with promises missed, late minutes, bay blocked, jobs moved, sourcing cost and slowest solve.
2. The numbers are read from files the experiments write (`experiments/out/eval_summary.json` and `scale_summary.json`), never typed into the frontend.
3. The page states in one line each: the shop is simulated; 200 seeded stalls; every plan passed the rule checker; how many solves were proven best.
4. The scale check (12 to 60 jobs, median and slowest re-plan time) is shown as a second small table from its own output file.
5. A one-sentence reading under each table, the same honest wording as the README: a fast source does most of the work; choosing both together keeps the same promises for about a third less sourcing cost and blocks the bay about 18 minutes longer.
6. The page loads without running the solver (it only reads files).
7. Works at phone width.

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/api/results` | `{benchmark: {stalls, methods: [{name, missed, late_min, bay_blocked_min, moved, cost, max_solve_s}], proven, checked}, scale: [{jobs, techs, bays, days, median_s, max_s, proven}]}` |

Returns 404 with a readable message if the experiment has not been run yet.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | `/api/results` returns the six methods and 200 stalls | `test_results_match_the_benchmark_output` (to write) |
| A2 | Every number equals the one in `experiments/out/` | same test |
| A3 | Missing output file gives 404, not a crash | `test_results_without_output_says_so` (to write) |
| A4 | Rules 3, 5 and 7 | manual check |

## Out of scope

Running the benchmark from the browser, charts with hover.

## Open questions

- Today `eval.py` writes `eval_results.csv` and `eval_summary.md`, and `scale.py` writes `scale_summary.md`. Step one is to make both also write JSON with the same numbers, then re-run them. Either reshape the CSV in the API instead, or add the JSON writers: owner decides.

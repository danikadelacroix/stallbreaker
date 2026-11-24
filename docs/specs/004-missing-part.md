# 004 Missing part (the stall flow)

**Status:** Built · **Code:** `backend/stalls.py`, `backend/sourcing.py`, `backend/risk.py` · **Tests:** `tests/test_api.py`

## Why

This is the core of the product: a part is missing, the manager sees every source and what each
plan costs in missed promises, approves once, and the day is re-planned.

## Rules

**Reporting**

1. Any open repair order and any part it uses can be reported missing.
2. Rejected with 404 if the order does not exist; 409 if the order does not use the part, the part is already on its way, the order is already waiting for a part, or it is finished.

**Sources**

3. Every sister store and supplier is listed with stock, arrival time (`eta_min`), cost and shortage risk. A sister store without enough stock is listed as unavailable.
4. Sister store cost is a $15 transfer fee. Supplier cost is its surcharge.
5. Shortage risk of a lending store = share of the part's 51 real months in which demand was more than the store would have left. `risk_basis` says it in words, for example "demand was above 0 in 36 of 51 past months".
6. A store above 30% risk is unsafe. Suppliers have zero risk.

**Plans**

7. The engine returns up to two options: `keep_promises` (fewest missed promises first) and `fewest_moves` (fewest jobs moved first). If both give the same plan, one option called "Recommended plan" is shown.
8. Each option has its source, arrival, cost, missed promises, late minutes, jobs moved (with before and after), bay blocked minutes, whether it is proven best, solve time, and every assignment.
9. Every option passes `validate` before it is returned.
10. A "no re-plan" comparison is included: what happens if the shop just waits for the cheapest safe source.
11. The manager can force any available source, including an unsafe one, and see what it costs. An unavailable source is rejected with 422.

**Proposals and approval**

12. The options are saved as an open proposal. A new report replaces any open proposal.
13. Approving one option makes it the live plan. For a job in progress, the work done so far and the blocked bay are stored as segments, and the job is pinned for later stalls.
14. The part is recorded as on its way and the lending store's stock goes down.
15. The log gets a `stall_resolved` entry with the decision, the jobs moved, and a draft message for every customer whose promise is newly missed. Messages come from a fixed template and say so.
16. A proposal can be approved once. A proposal made before the plan changed (older `plan_version`) cannot be approved: 409, report again.
17. A proposal can be dismissed without deciding.
18. A later stall plans around earlier ones: the earlier stalled job does not move and its bay stays blocked.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/stalls` | `{ro_id, part_id, force_source?}` | the proposal |
| GET | `/api/proposals/{id}` | | the proposal |
| POST | `/api/proposals/{id}/approve` | `{option}` | `{decided, day}` |
| POST | `/api/proposals/{id}/dismiss` | | the day |

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rules 3 to 10 on the demo stall: North unsafe, East safe, best plan proven, not North, beats no re-plan, resumes after arrival in the same bay | `test_stall_on_a_job_in_progress_offers_sources_and_a_checked_plan` |
| A2 | Rules 2 and 11 | `test_forcing_a_source_is_honoured_and_rejected_when_impossible` |
| A3 | Rules 13 to 16 | `test_approving_a_plan_changes_the_day_and_is_recorded` |
| A4 | Rule 18 | `test_a_second_stall_plans_around_the_first` |
| A5 | Rules 12, 16 and 17 | `test_a_stale_proposal_cannot_be_approved` |

Demo numbers (seed 2026, clock at 11:00, RO-1013 gasket kit): recommended source Local vendor, $85,
1 promise missed by 30 min, 1 job moved, bay blocked 1 h. No re-plan: 2 missed, 375 late
minutes, bay blocked 4 h. North is unsafe at 71% (36 of 51 months).

## Out of scope

Splitting one part order across sources, partial quantities, supplier stock checks.

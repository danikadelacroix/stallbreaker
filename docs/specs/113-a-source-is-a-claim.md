# 113 A source is a claim until the part is here

**Status:** In progress · **Owner:** danikadelacroix · **Depends on:** 003, 004, 005, 107, 108 · **Changes:** 005 (a late part may now change source)

## Why

When a manager approves "Local vendor, arriving 12:00", the app has so far treated 12:00 as a
fact. It is only a request. The source may confirm it, give a later time, say it cannot supply
the part, not answer, or say yes and still not deliver. A manager needs to know which parts are
only requested, how long there is still a way back, and what the day looks like with another
source when the first one fails.

## Rules

**A request and its three states**

1. Every ordered part is a request. It is `requested` when placed (ordered ahead in 003, by approving a plan in 004, or by a change of source here), `confirmed` when a person records that the source said yes, and `received` when a person records that the part is in the building. The job panel shows the state.
2. For each request the app works out, from the plan as it stands, when the part is needed: the time its job is due to start or resume (`needed_by_min`). A part that arrives by then changes nothing in the plan (005 rule 3).
3. Each request names a backup: the fastest other safe source that has the part, leaving out a source that has already said it cannot supply this request. Its switch-by time (`switch_by_min`) is `needed_by_min` less the backup's delivery time: order the backup by then and the plan holds exactly as it is. If that moment had already passed when the order was placed, the screen says there is no way back that leaves the plan untouched, and how long the backup would take.
4. Every plan option shows its backup and switch-by time before it is approved, next to how late the part can be (108), so a plan with no way back can be told apart from one with hours of room.
5. Nothing is reserved at the backup, and passing the switch-by time changes nothing by itself. Both values are worked out afresh whenever they are shown, so they follow the plan when it changes.

**Chasing**

6. A request needs chasing when it is still `requested` at its switch-by time, or at its arrival time if that is earlier or there was no way back to begin with (`no_answer`); and when it is not `received` at its arrival time (`not_here`). The day lists these until the part is received or the job is done.

**Recording the answer**

7. A person records what the source said: confirmed, received, a new time, or cannot supply. Confirmed and received change the state only; the plan is not touched, the answer goes in the log, and any open proposal for that part is closed.
8. A new time the plan can absorb (the part still arrives by `needed_by_min`) is recorded as in 005, and the request is confirmed, since the source gave the time.
9. A new time the plan cannot absorb, a source that cannot supply, or a manager who has waited long enough, all lead to the same thing: the source is re-planned.

**Re-planning the source** (this replaces "it keeps its source" in 005)

10. A request can be re-planned under the conditions of 005 rule 2. In the running are every other source that has the part, each timed from now, and the current source: at its new time if it gave one; at its recorded time if it gave none and that time is still ahead; not at all if it cannot supply. The current source is taken from the request, not from the stock table, and staying with it costs nothing new.
11. The result is a proposal like any other: the source table with the outcome of each source and why the engine did not choose it (107), plans to approve (004 rules 12 to 17), and the manager may force a source, including staying with the current one while it is in the running.
12. A car already waiting in its bay stays there (005 rule 6). Bays and technicians busy with another car that is being rolled out stay blocked.
13. Approving a plan that keeps the source records its new time, and confirms the request if the source gave that time; the log entry is `part_late_replanned`. Approving a plan with another source cancels the old request and places the new one as `requested`; the log entry is `source_switched`, with both sources, the cost, and what a person must now do by hand (cancel with the old source, order from the new one). A sister store whose request is cancelled gets the part back on its count, unless it said it cannot supply it.
14. If the clock has passed the start of a job whose part was never received, the job has been taken apart without it. That is a missing part (004): reporting it replaces the request when a plan is approved, and the old store gets the part back on its count.
15. The app never contacts a source. Asking, chasing, ordering and cancelling are done by a person.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/day` | | each part need gains `request`: `null`, or `{state, source_id, source_name, arrives_min, needed_by_min, switch_by_min, backup_name, backup_eta_min, chase}` with `chase` one of `null`, `no_answer`, `not_here`; `summary.requests_to_chase` |
| POST | `/api/stalls`, `/api/late/replan` | | each plan option gains `needed_by_min`, `switch_by_min` (`null` when it is not later than now), `backup_name`, `backup_eta_min` |
| POST | `/api/requests/answer` | `{ro_id, part_id, answer}` with `answer` `confirmed` or `received` | `{day}`; 409 if no part is on its way for that job |
| POST | `/api/late/confirm` | as 005 | as 005; the request also becomes `confirmed` |
| POST | `/api/late/replan` | `{ro_id, part_id, arrives_min?, cannot_supply?, force_source?}` | a `late_part` proposal that now lists every source, with `why` one of `new_time`, `cannot_supply`, `no_answer`, and `old_source_id`, `old_source_name`; 409 if a new time is given that the plan can absorb; 422 if the forced source is not in the running |

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rules 1, 7: a part ordered by approving a plan, and one ordered ahead, are `requested`; an answer makes them `confirmed`, then `received`, without touching the plan | `test_an_ordered_part_is_only_requested_until_a_person_says_otherwise` |
| A2 | Rules 2, 3: `needed_by_min` is the job's start, and `switch_by_min` is that less the delivery time of the fastest other safe source | `test_a_request_says_when_the_part_is_needed_and_the_last_moment_to_switch` |
| A3 | Rules 3, 4: a plan with no way back says so before approval, and what an option shows is what the request shows after approval | `test_a_plan_says_before_approval_whether_there_is_a_way_back` |
| A4 | Rule 3: ordering the named backup at the switch-by time leaves the plan exactly as it is | `test_ordering_the_backup_at_the_switch_by_time_leaves_the_plan_as_it_is` |
| A5 | Rule 6: `no_answer` at the switch-by time, `not_here` at the arrival time, neither once received | `test_a_request_needs_chasing_when_unanswered_or_not_here` |
| A6 | Rule 8 | `test_a_new_time_the_plan_can_absorb_is_recorded_and_confirms_the_request` |
| A7 | Rules 10, 12, 13: a source that cannot supply, for a car waiting in its bay: it is out of the running and is not the new backup, the car stays put, the plan passes the engine's checker, the new request is `requested`, the log says what to do by hand | `test_a_source_that_cannot_supply_is_replaced_for_a_car_waiting_in_its_bay` |
| A8 | Rules 10, 11, 13: a new time the plan cannot absorb: the old source competes at its new time, every source has an outcome, and the manager can stay with it | `test_a_new_time_the_plan_cannot_absorb_puts_the_old_source_up_against_the_others` |
| A9 | Rules 10, 11: no answer: the current source competes at its recorded time; a source that cannot supply cannot be forced | `test_with_no_answer_the_current_source_stays_in_the_running_at_its_recorded_time` |
| A10 | Rule 13: a sister store gets its part back when its request is cancelled, but not when it said it cannot supply | `test_a_cancelled_sister_store_gets_its_part_back_unless_it_said_no` |
| A11 | Rule 14 | `test_a_job_taken_apart_without_its_part_is_a_missing_part_that_replaces_the_request` |

## Limits we know about

- Delivery times are fixed per source. Real shuttle and vendor runs leave at set times, so "the last moment to order the backup" is really "the last run".
- An OEM depot usually confirms an order electronically at once. Here it starts as `requested` like any other.
- Two requests can name the same backup. Nothing is reserved until a person orders it.
- A job not yet taken apart cannot start earlier than its first source promised, even when a faster source replaces it.

## Out of scope

Reading a source's reply from pasted text. The note box (112) already reads "the part will be
late" for a part on its way, and that now leads here; teaching it "confirmed" and "cannot
supply" is a later step. Remembering that a supplier said no when the same part is needed
again later in the day (a sister store is remembered, through its count). Rolling a waiting car
out of its bay as part of a change of source. Counting "no way back" among the reasons a plan
needs a person (111). Sending anything to a source.

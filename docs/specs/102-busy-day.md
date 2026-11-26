# 102 Busy demo day

**Status:** Not planned · **Owner:** unassigned · **Depends on:** 002

Not planned (24 Nov 2026): a second, busier day is a lot of work and shows little that today's
day does not. The README states the limit instead. The rules below are kept in case it comes back.

## Why

On today's demo day most stalls move one or two jobs, because the shop is lightly loaded. On a
busy day the trade-offs are sharper and the engine's value is easier to see.

## Rules

1. Reset can build either day: `normal` (today's) or `busy`. Default stays `normal` so nothing breaks.
2. The busy day has about 55 to 60 repair orders on the same 10 technicians and 10 bays, so the morning plan is tight but still keeps every promise.
3. The busy day is seeded and repeatable, like the normal one.
4. It has at least one designed stall where the fastest source is the wrong choice: a slower, cheaper source keeps the same promises because the schedule can absorb the wait.
5. It has at least one stall where no plan keeps every promise, so the two plan options differ.
6. Every repair order and part combination on the busy day solves within 5 seconds (see 104).
7. The header shows which day is loaded.

## API

`POST /api/reset?day=busy` (and `day=normal`). Invalid value → 422.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Busy day has 55 to 60 orders, a valid plan, no promise missed in the morning | `test_busy_day_has_a_full_valid_plan` (to write) |
| A2 | Two resets give the same busy day | `test_busy_day_is_repeatable` (to write) |
| A3 | Rule 4: the recommended source is not the fastest, and the fastest gives no fewer missed promises | `test_busy_day_has_a_stall_where_fastest_is_wrong` (to write) |
| A4 | Rule 5: the two options differ | `test_busy_day_has_a_real_trade_off` (to write) |
| A5 | The normal day is unchanged (all current tests still pass) | existing suite |

## Out of scope

Real dealership volumes, more stores.

## Open questions

- Exact designed stalls: pick them by running the engine over candidate seeds and keeping one that meets rules 4 and 5. Owner decides and writes the chosen RO numbers here.

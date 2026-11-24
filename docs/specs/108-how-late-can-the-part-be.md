# 108 How late can the part be?

**Status:** Built · **Owner:** danikadelacroix · **Depends on:** 004, 005

## Why

Arrival times are promises from someone else, and they slip. Probability curves for delays
need data nobody has yet. A manager needs one number instead: how late can this part be
before the plan costs another customer's promise?

## Rules

1. Every plan option carries `late_margin_min`: the longest delay of the part, in 15-minute steps up to 4 hours, after which the day can still be re-planned with no more missed promises than the option has now.
2. The margin is found by re-planning with the later arrival, not by reading slack off the chart. A delay inside the margin may still move jobs; it never costs a promise.
3. `late_margin_capped` is true when the margin reached the 4-hour limit.
4. A margin of 0 means any delay of 15 minutes costs another promise.
5. The margin agrees with the late-part flow (005): after the plan is approved, a part late by the margin does not add a missed promise; late by one step more, it does.

## API

Each plan option gains `late_margin_min` (0 to 240) and `late_margin_capped`. Each source's
`outcome` (107) carries the same two fields, so a cheap source with no slack can be compared
with a dearer one that has hours of it.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rules 1, 3: a multiple of 15 between 0 and 240 | `test_a_plan_says_how_late_the_part_can_be` |
| A2 | Rule 5 | same test |

## Out of scope

Probabilities of delay. Choosing between sources by margin (a later spec could break ties on it).

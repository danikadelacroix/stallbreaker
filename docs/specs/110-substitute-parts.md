# 110 Substitute part numbers

**Status:** Not planned · **Owner:** unassigned · **Depends on:** 004

Not planned (24 Nov 2026): we have no real table of which part numbers replace which, and an
invented one would be a fitment and warranty claim we cannot back. The rules below are kept in
case a real table turns up.

## Why

Often the fastest source is the shop's own shelf: a newer part number that replaces the missing
one. In our engine a substitute is just one more source, so it costs little to add.

## Rules

1. A small table lists which part numbers replace which. Replacement is one-way unless marked two-way: the newer number can replace the older, not the other way round.
2. A substitute in stock at the home store is a source with zero travel time. A substitute at a sister store is a source like any other, with its own shortage risk.
3. Only listed substitutes are ever offered. The engine never guesses fitment.
4. The source table shows the substitute's part number and the rule that allows it.
5. A substitute that is listed but not allowed for this direction is shown as rejected with the reason.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | A stall with a substitute on the home shelf is solved with no wait | to write |
| A2 | The older number is never offered for the newer | to write |
| A3 | Without substitutes for a part, results are unchanged | existing suite |

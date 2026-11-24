# 107 Why not this source?

**Status:** Built · **Owner:** danikadelacroix · **Depends on:** 004

## Why

Most tools rank sources with a score. A manager does not trust a score; they ask "why not the
store down the road?" We can answer with facts, because the engine can plan the day for each
source in a fraction of a second.

## Rules

1. For every source that has the part, the proposal says what the day would look like if that source were used: promises missed, late minutes, jobs moved, bay blocked, cost, arrival.
2. Each outcome is a real re-plan by the engine with that source forced, checked by `validate`. It is never an estimate.
3. Every source the engine did not choose has one plain sentence saying why, and the sentence names the first goal on which it loses, in the engine's own goal order: unsafe to lend, more promises missed, more late minutes, higher cost, more jobs moved.
4. A source that ties the chosen one on all of those says so.
5. The proposal names the engine's own pick (`engine_source_id`) even when the manager has forced another source.
6. Sources without the part have no outcome.
7. The whole proposal still returns within 5 seconds on the demo day.

## API

Each entry in `sources` gains `outcome` (`{missed_promises, late_minutes, jobs_moved, bay_blocked_min, cost, arrives_min, proven_best}` or null) and `why_not` (string or null). The proposal gains `engine_source_id`.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rules 1, 2, 6: available sources have outcomes, others none; the chosen source's outcome equals the recommended plan | `test_every_source_says_what_the_day_would_look_like` |
| A2 | Rules 3, 4: every other source has a reason; the unsafe store's reason says unsafe; no safe source beats the chosen one | same test |
| A3 | Rule 5 | `test_forcing_a_source_still_names_the_engines_pick` |
| A4 | Rule 7 | `test_a_proposal_comes_back_within_five_seconds` |

## Out of scope

An LLM writing the sentence (103 may rephrase it, never change it).

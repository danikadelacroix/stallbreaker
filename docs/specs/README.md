# Specs

Each feature of StallBreaker has a spec here: what it must do, written as numbered rules, and
the acceptance checks that prove it. A rule that matters has a test with a matching name.

New work starts here. Write or update the spec, get it reviewed, then write the failing test,
then the code. See [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full loop.

## Index

| Spec | Status | Tests |
|---|---|---|
| [001 Re-planning engine](001-engine.md) | Built | `tests/test_stallbreaker.py` |
| [002 Demo day and API basics](002-demo-day-and-api.md) | Built | `tests/test_api.py` |
| [003 Parts check](003-parts-check.md) | Built | `tests/test_api.py` |
| [004 Missing part](004-missing-part.md) | Built | `tests/test_api.py` |
| [005 Late part](005-late-part.md) | Built | `tests/test_api.py` |
| [006 Web app](006-web-app.md) | Built | manual checks (no UI tests yet) |
| [101 Results page](101-results-page.md) | Proposed | |
| [102 Busy demo day](102-busy-day.md) | Not planned | |
| [103 Plan explanation and customer message (LLM)](103-llm-explanations.md) | Proposed | |
| [104 Every demo case solves](104-every-case-solves.md) | Fast version built | `tests/test_api.py` |
| [105 Run anywhere: deployed and offline](105-deploy-and-offline.md) | Proposed | |
| [106 UI tests](106-ui-tests.md) | Proposed | |
| [107 Why not this source?](107-why-not-this-source.md) | Built | `tests/test_api.py` |
| [108 How late can the part be?](108-how-late-can-the-part-be.md) | Built | `tests/test_api.py` |
| [109 Hold the bay, or roll the car out?](109-hold-or-release-the-bay.md) | Built | `tests/test_stallbreaker.py`, `tests/test_api.py` |
| [110 Substitute part numbers](110-substitute-parts.md) | Not planned | |
| [111 Act alone, or ask](111-act-alone-or-ask.md) | Rule 3 built; acting alone not planned | `tests/test_api.py` |
| [112 Read the note](112-read-the-note.md) | Built with the rules reader; no model scored yet | `tests/test_intake.py` |
| [113 A source is a claim until the part is here](113-a-source-is-a-claim.md) | Built | `tests/test_claims.py` |
| [114 Read a source's reply](114-read-a-source-reply.md) | Built | `tests/test_intake.py` |
| [115 Landing page, light and dark theme](115-landing-page-and-theme.md) | Built | manual checks |
| [116 Role views and voice](116-role-views.md) | Built | manual checks |

Status moves Proposed → Agreed (both of us have read it) → In progress (owner named) → Built
(every acceptance check has a passing test, or a manual check written down in the spec).
A spec we decided not to build says Not planned, with the reason at the top.

## Words used in every spec

| Word | Meaning |
|---|---|
| Repair order (RO) | One job on one car, for example `RO-1013` water pump replacement. |
| Promise time | When the customer was told the car would be ready. Missing it is the worst outcome. |
| Bay | A lift or flat bay. A car that has been taken apart cannot leave its bay. |
| Stall | A job that cannot go on because a part is missing. |
| Source | Where a part can come from: a sister store, the local vendor, or the OEM depot. |
| Shortage risk | Share of the 51 real past months in which a lending store's demand was more than it would have left. Above 30% the store is unsafe to borrow from. |
| Plan | Start time, technician and bay for every job, plus where each missing part comes from. |
| Proposal | The plan options offered for one stall, saved until approved, dismissed or replaced. |
| Plan version | A counter that goes up each time a plan is approved. A proposal made on an older version cannot be approved. |
| Minutes | All times are minutes after 08:00. 150 is 10:30. |

## Template

Copy [000-template.md](000-template.md) for a new spec. Keep it short: rules a reviewer can
check, not an essay.

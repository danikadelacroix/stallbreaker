# 112 Read the note

**Status:** Built with the rules reader; no model scored yet · **Owner:** danikadelacroix · **Depends on:** 004, 005 · **Code:** `backend/intake.py`, `backend/llm.py`

## Why

A stall does not start with a click. It starts with a technician typing or saying something
like "1013 wp off, gskt kit in bin is for the 2.0 not 2.5t". Someone then has to work out which
repair order and which part that means. The app should do that reading, show what it understood,
and let a person confirm it before anything else happens.

## Rules

**What a reading is**

1. A note is read into: what happened (`missing_part`, `late_part` or `unclear`), the repair order, the part, a new arrival time for a late part, and the exact words the reading rests on (`quote`).
2. Reading changes nothing. No stall is opened, nothing is saved, and the plan is not touched until a person confirms the reading. Confirming uses the existing stall flow (004) or late-part flow (005).
3. A note that cannot be read with confidence is `unclear`, with the reason in plain words. An unclear reading is never opened.

**What a reader may and may not do**

4. The repair order must be one that is open today, and the part must be one that order needs. Anything else is `unclear`.
5. A late part must already be on its way for that order, and its new time must be later than now.
6. The quote must appear word for word in the note.
7. Rules 4 to 6 are checked in code for every reader. A model's answer that fails them is thrown away.

**Readers**

8. A rules reader works with no key and no internet: it finds the repair order by number, or by vehicle, bay, job or technician, and the part by its name and common shorthand.
9. A model reader can be switched on with a key in the environment. It chooses only from the lists the code gives it: the open repair orders and the parts each one needs.
10. If the model is not set up, times out, or gives an answer that fails the checks, the rules reader is used and the screen says so. A fallback is never silent.
11. Phone numbers, email addresses and vehicle identification numbers are removed from the note before it leaves the machine. The note box says when a note is sent to a provider.
12. The reader never decides the source, the schedule or any time in the plan.

**The test set**

13. `tests/intake_cases.jsonl` holds real-sounding notes with the reading each should give, including notes that must come out `unclear`. There are three groups. `dev` and `held_out` were written by the same people as the reading rules, and the rules may be tuned on `dev` only. `outside` was written by someone who saw only the day's jobs and parts. It is frozen: nothing is ever tuned on it, its misses are reported by kind and not listed, and it is the score to quote.
14. `experiments/intake_eval.py` scores a reader on all three groups and writes the result. The app shows which reader is in use and its score on the outside notes.
15. Automated tests never call a real model. They use a stand-in that returns set answers, including wrong ones.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/intake` | `{text}` (up to 600 characters) | `{kind, ro_id, part_id, part_name, vehicle, description, arrives_min, quote, why_unclear, read_by, fell_back_because}` |
| GET | `/api/intake/info` | | `{reader, sends_notes_out, eval}` |

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rules 1, 6, 8: a shorthand note is read to the right order and part, with a quote from the note | `test_a_shorthand_note_is_read_to_the_right_job_and_part` |
| A2 | Rule 2: reading saves nothing | `test_reading_a_note_changes_nothing` |
| A3 | Rules 3, 4: no such order, a part the order does not need, or no part at all is unclear with a reason | `test_a_note_that_cannot_be_read_says_why` |
| A4 | Rule 5: a late part is read with its new time | `test_a_note_about_a_late_part_is_read_with_its_new_time` |
| A5 | Rules 7, 10: a model answer with a wrong order or an invented quote is thrown away and the fallback is named | `test_a_wrong_model_answer_is_thrown_away_and_the_fallback_is_named` |
| A6 | Rule 9: a model answer that passes is used and labelled | `test_a_good_model_answer_is_used_and_labelled` |
| A7 | Rule 11 | `test_personal_details_are_removed_before_a_note_is_sent` |
| A8 | Rules 13, 14: the score file matches a fresh run of the rules reader | `test_the_published_score_matches_the_rules_reader` |

## Where it stands

The rules reader gets 34 of 34 of our own notes and 32 of 40 of the outside notes. The gap is the point of the outside group. A model reader has to beat 32 of 40 on the same notes to be worth switching on, and it is scored the same way.

## Out of scope

A part the repair order does not list (common in real shops, and next on the list). Several
parts in one note. Sound: dictation uses the browser's own speech-to-text into the same box.
A source's reply about a part already ordered is read as in 114.

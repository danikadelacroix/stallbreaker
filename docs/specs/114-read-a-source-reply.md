# 114 Read a source's reply

**Status:** Built · **Owner:** danikadelacroix · **Depends on:** 112, 113 · **Changes:** 112 (new kinds of reading), 113 (out of scope: reading a reply) · **Code:** `backend/intake.py`

## Why

Once a part is ordered (113), the next thing that happens is a reply: a text from the sister
store, a call from the vendor, a word at the parts counter. "North confirmed the tensioner."
"Vendor can't get the gasket kit." "Pads from East are here." Today someone has to find the job
and press the right button. The note box (112) already reads technicians' notes; it should read
these replies the same way, show what it understood, and lead to the button that 113 already has.

## Rules

**What a reply is read as**

1. A reply is a note about a part that has been ordered, with words that say what the source said or that the part came: confirmed, on its way, here, arrived, cannot get, sold out and the like. A note about an ordered part without such words is read as in 112. A reply is read as `confirmed` (the source said yes), `received` (the part is in the building), `cannot_supply` (the source cannot send it), or `late_part` as before (112), when it gives a time later than the one recorded. "Confirmed for 12:30" with 12:20 recorded is `late_part`; with 12:20 or earlier it is `confirmed`, and the earlier time is not recorded.
2. When a reply says more than one thing, the first of these wins: a time later than the recorded one ("can't get it till 14:00" is late), cannot supply, received, confirmed. A reply that says the part is here ignores any time in it.
3. Words that deny never count as a yes: "not here", "hasn't confirmed", "no answer", "not arrived" are not `received` or `confirmed`. This is checked on the quoted words for every reader.

**Which request it is about**

4. The repair order is found as in 112 (number, vehicle, bay, technician), but only among jobs that have the part on order; when the note names none of these, all such jobs are candidates. A part not yet received counts before one already here, and the source narrows it further if the note names one. There must then be exactly one that fits. More than one is `unclear`, asking for the repair order number; the 112 tie-break for a job in progress does not apply.
5. If the note names a source, it must be the source the part was ordered from. Otherwise the reading is `unclear` and says where the part was ordered from. Sources are named as: "north" or "sister store north"; "east" or "sister store east"; "vendor" or "local vendor"; "oem", "depot" or "oem depot".
6. A reply about a part already received is `unclear`, and so is `confirmed` for a part already confirmed. `cannot_supply` for a job already under way is `unclear` and says to report the part missing from the job panel, because the car is already apart (113 rule 14). A car waiting in its bay for the part is not under way: its source can be re-planned (113 rule 12). A `late_part` for a received part is `unclear`.

**What it may do**

7. Reading saves nothing (112 rule 2). Confirming a reading uses what 113 already has: `confirmed` and `received` record the answer; `cannot_supply` opens a proposal with every other source and nothing else changes until a plan is approved; `late_part` checks the plan as before. If that step refuses (for example the job has just started), the reason is shown.
8. Every reader passes the same checks in code (112 rule 7): rules 3, 5 and 6 here, plus the quote check. A model is told, for each ordered part, its source, its recorded time and its state.

**The test set**

9. New notes for replies go into the `dev` and `held_out` groups. The `outside` group is not changed and is scored exactly as before: its notes were labelled before replies could be read, so a note there read as a reply counts as a miss. Its score is published again after this change, whatever it is, and nothing is tuned on it.

## API

`POST /api/intake` returns the same fields as in 112, with `kind` now one of `missing_part`,
`late_part`, `confirmed`, `received`, `cannot_supply` or `unclear`, and one more field,
`source_name`: where the part was ordered from (null for `missing_part` and `unclear`).

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rules 1, 4: "north confirmed the tensioner" is read as confirmed for RO-1017 with no repair order number | `test_a_reply_is_read_to_the_right_request` |
| A2 | Rule 1: received and cannot supply are read, with the source named | `test_a_reply_is_read_to_the_right_request` |
| A3 | Rules 1, 2: a confirm or a "can't get it till" with a later time is late; the recorded time is not | `test_a_confirm_with_a_later_time_is_late` |
| A4 | Rules 3, 4, 5, 6: a denial, two matching requests, the wrong source, confirmed twice, a part already received, and cannot supply for a job under way are unclear, each with a reason; a part already here does not block a reply about another job | `test_a_reply_that_cannot_be_read_says_why` |
| A5 | Rule 7: reading a reply saves nothing | `test_reading_a_reply_changes_nothing` |
| A6 | Rule 8: a model's reply reading is used when it passes and thrown away when it names a part not on its way | `test_a_model_reply_reading_is_checked` |
| A7 | Rule 9: the score file matches a fresh run, and the outside group has its 40 notes | `test_the_published_score_matches_the_rules_reader` |
| M1 | Manual: a confirmed or received reply, once confirmed, changes the job panel, chase strip and log as the button does; a cannot-supply reply opens the same proposal as the button | checked 28 Nov 2026, see below |

## Where it stands

Built in the rules reader and in the checks every reader passes; the model reader is told each
ordered part's source, time and state. On the demo day at 11:00 with the parts check ordered,
"north confirmed the tensioner" read as RO-1017 and, once confirmed, the job panel showed
"Confirmed by the source" and the log recorded it. "east cant get the brake pads for 1040" opened
the same proposal as the Cannot supply button: Local vendor at 12:00, no promise missed.

All 14 reply notes in `dev` and `held_out` read right. They were written alongside the rules, so
that says little; the outside score did not move (32 of 40, misses unchanged by kind).

## Out of scope

Replies that name several parts or several orders at once. A reply with no part named ("north
says yes"), even when only one request is open from that source. Reading a supplier's email
thread. Sending anything back to a source.

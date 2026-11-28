# 114 Read a source's reply

**Status:** Proposed · **Owner:** danikadelacroix · **Depends on:** 112, 113 · **Changes:** 112 (new kinds of reading), 113 (out of scope: reading a reply) · **Code:** `backend/intake.py`

## Why

Once a part is ordered (113), the next thing that happens is a reply: a text from the sister
store, a call from the vendor, a word at the parts counter. "North confirmed the tensioner."
"Vendor can't get the gasket kit." "Pads from East are here." Today someone has to find the job
and press the right button. The note box (112) already reads technicians' notes; it should read
these replies the same way, show what it understood, and lead to the button that 113 already has.

## Rules

**What a reply is read as**

1. A reply is a note about a part that has been ordered and not yet received. It is read as `confirmed` (the source said yes), `received` (the part is in the building), `cannot_supply` (the source cannot send it), or `late_part` as before (112), when it gives a time later than the one recorded. "Confirmed for 12:30" with 12:20 recorded is `late_part`; with 12:20 or earlier it is `confirmed`.
2. When a reply says more than one thing, the first of these wins: cannot supply, a later time, received, confirmed.
3. Words that deny never count as a yes: "not here", "hasn't confirmed", "no answer", "not arrived" are not `received` or `confirmed`.

**Which request it is about**

4. The repair order is found as in 112 (number, vehicle, bay, technician). When the note names none of these, the request is found by the part, and by the source if the note names one: there must be exactly one open request that fits. More than one is `unclear`, asking for the repair order number.
5. If the note names a source, it must be the source the part was ordered from. Otherwise the reading is `unclear` and says where the part was ordered from.
6. A reply about a part already received is `unclear`, and so is `confirmed` for a part already confirmed. `cannot_supply` for a job already under way is `unclear` and says to report the part missing from the job panel, because the car is already apart (113 rule 14). A `late_part` for a received part is `unclear`.

**What it may do**

7. Reading saves nothing (112 rule 2). Confirming a reading uses what 113 already has: `confirmed` and `received` record the answer; `cannot_supply` plans the day again with every other source; `late_part` checks the plan as before.
8. Every reader passes the same checks in code (112 rule 7): rules 1, 5 and 6 here, plus the quote check. A model chooses only from the open requests it is given, with their sources.

**The test set**

9. New notes for replies go into the `dev` and `held_out` groups. The `outside` group is not changed and is scored exactly as before: its notes were labelled before replies could be read, so a note there read as a reply counts as a miss.

## API

`POST /api/intake` returns the same fields as in 112, with `kind` now one of `missing_part`,
`late_part`, `confirmed`, `received`, `cannot_supply` or `unclear`, and one more field,
`source_name`: where the part was ordered from (null for `missing_part` and `unclear`).

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rules 1, 4: "north confirmed the tensioner" is read as confirmed for RO-1017 with no repair order number | `test_a_reply_is_read_to_the_right_request` |
| A2 | Rule 1: received and cannot supply are read, with the source named | `test_a_reply_is_read_to_the_right_request` |
| A3 | Rules 1, 2: a confirm with a later time is late | `test_a_confirm_with_a_later_time_is_late` |
| A4 | Rules 3, 4, 5, 6: a denial, two matching requests, the wrong source, and a part already received are unclear, each with a reason | `test_a_reply_that_cannot_be_read_says_why` |
| A5 | Rule 7: reading a reply saves nothing | `test_reading_a_reply_changes_nothing` |
| A6 | Rule 8: a model's reply reading is used when it passes and thrown away when it names a part not on its way | `test_a_model_reply_reading_is_checked` |
| A7 | Rule 9: the score file matches a fresh run, and the outside group has its 40 notes | `test_the_published_score_matches_the_rules_reader` |
| M1 | Manual: type a reply, confirm it, and the job panel, chase strip and log change as when the button is pressed | written down below once checked |

## Out of scope

Replies that name several parts or several orders at once. A reply with no part named ("north
says yes"), even when only one request is open from that source. Reading a supplier's email
thread. Sending anything back to a source.

# 116 Role views and voice

**Status:** Built · **Owner:** danikadelacroix · **Depends on:** 006, 112, 113, 114, 115 · **Code:** `frontend/src/roles/`, `frontend/src/App.tsx`

## Why

Three people handle a stalled job: the technician who finds the problem, the service manager who
decides, and the parts counter who follows the order. Until now all three worked from one dense
screen. Each should open the app and see their own part of the job, in their own words.

## Rules

**Entering**

1. "Open the demo" leads to a role picker at `/demo`: three cards, each saying who the person is and what they do here. Each role has its own address (`/demo/manager`, `/demo/technician`, `/demo/parts`), and the header of every view can switch role.
2. These are demo roles. There is no sign-in, and the limits below are limits of each screen, not access control on the API. The picker says so.
3. All roles share the one demo day. What one role does shows up in the others: each view checks for news every few seconds while its tab is visible.

**Technician**

4. The technician first picks who they are from the day's technicians (remembered on that browser), and sees their own jobs for the day in order: repair order, vehicle, job, bay, time and status, and each part with where it stands.
5. They can report a problem by typing or by voice (rule 13). The note is read as in 112 and they confirm what was understood. A confirmed missing part is sent to the service manager; the technician sees that it is waiting for a decision and never sees the plans, the sources or any cost.
6. Each part on their own open jobs also has a plain "Report missing" button, for when the note cannot be read.
7. Once the manager approves, the job shows its new time and bay and when the part arrives. A technician can record that an ordered part for their job is here.
8. While another stall is waiting for the manager, reporting is paused and the screen says why.

**Parts counter**

9. The parts counter sees every ordered part in one list: job, part, source, when it is due, whether it is requested, confirmed or received, when it is needed, and the last moment to switch to the backup (113). Parts that need chasing come first.
10. They record what a source said, by button or by pasting the reply into the note box (114): confirmed, here, a new time the plan can absorb. News the plan cannot absorb (a later time that breaks it, cannot supply, no answer) is sent to the service manager as a proposal; the parts counter does not see or approve plans.
11. They see the parts check (003) and may order ahead the parts that need no re-plan: a safe source, in time, and within the spending limit. Shortfalls that need a decision are shown as waiting for the manager.

**Service manager**

12. The service manager's view is the full screen as before: what needs a decision, the plans, the board, the clock and the log. Nothing is locked.

**Voice**

13. The note box has a push-to-talk button where the browser supports speech recognition (Chrome, Edge, Safari). Speech is turned into text in the box by the browser, in Indian English, and is then read exactly like a typed note; the person still confirms the reading. Where the browser has no speech recognition the button is not shown and typing works as before.
14. The app sends no audio anywhere itself. The screen says that the browser's own speech service does the listening.

## Acceptance checks

| # | Check | How |
|---|---|---|
| M1 | Rules 1, 2: the picker, the three addresses (also loaded directly), the switcher | manual, local and hosted |
| M2 | Rules 4 to 7: as Pooja, report RO-1013's gasket kit; the view says it is waiting, shows no plan or cost; after approval as manager it shows the new time, bay and arrival | manual |
| M3 | Rule 8: with a stall open, another report is refused with the reason | manual |
| M4 | Rules 9, 10: as parts counter, confirm a part by button and by pasted reply; a cannot-supply reply goes to the manager and no plan is shown | manual |
| M5 | Rule 11: order ahead from the parts counter; a shortfall that needs a decision has no button | manual |
| M6 | Rule 3: a report made in one tab appears in the manager's tab without a reload | manual |
| M7 | Rule 13: the mic button appears in Chrome, fills the box, and the reading follows; hidden when unsupported | manual; speech itself cannot be automated |
| M8 | Both themes and 375 px width on every view, no sideways scroll | manual |

## Where it stands

Checked on 28 Nov 2026 in Chrome with a scripted run across three open tabs. As Pooja, "1013 no gasket
kit" was confirmed and sent; the technician's screen showed "Waiting for a decision", no plan and no
price, and paused further reports with the reason (M2, M3). The manager's tab showed the stall within
seconds without a reload and approved it (M6); the technician's tab then showed Bay 4, 11:30 to 14:30 and
"Arriving 11:30 from Local vendor" (M2). At the parts counter, ordering ahead filled the list, a pasted
reply and a button each confirmed a part, and "east cant get the brake pads for 1040" went to the manager
with no plan shown (M4, M5). The picker, the three addresses and the switcher work (M1); no view scrolls
sideways at 375 px in either theme (M8). The Speak button appears in Chrome (M7); speech itself was not
tested by script and needs a try by hand with a microphone.

## Out of scope

Real sign-in and access control on the API. Recording in the log which role did what. More than one
stall waiting for a decision at a time. A separate address per technician.

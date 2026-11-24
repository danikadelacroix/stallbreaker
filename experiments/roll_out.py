"""When does rolling a stalled car out of its bay pay?

Run:  .venv/bin/python experiments/roll_out.py [N]
Writes experiments/out/roll_out_summary.md.

Same seeded days and stalls as eval.py, but only the stalls where the car can be made movable
(our assumption per job type, see shopgen.MOVABLE). Two things are varied: how many lift bays
the shop has, and how far away the part is at best. For each setting the day is planned twice:
always holding the bay, and letting the engine choose between holding and rolling out.
The shop is simulated, so this shows where the choice matters, not what a real dealer would save.
"""
import os
import sys
from dataclasses import replace
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shopcore import Stall, hold_or_roll_out, metrics, replan, validate
from shopgen import make_day, make_stall

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
JOINT = ("late", "tard", "cost", "moves", "shift", "hold")
LIFT_BAYS = (3, 2)
PART_AT_LEAST = (0, 120, 240, 360)  # minutes; 0 keeps the generated arrival times


def one(args):
    seed, n_lift, wait = args
    rng, shop, jobs, base = make_day(seed, n_lift=n_lift)
    if base is None:
        return None
    now, stall = make_stall(rng, jobs, base)
    if stall is None or next(j for j in jobs if j.id == stall.job).roll_out is None:
        return None
    stall = Stall(stall.job, stall.part, tuple(replace(s, eta=max(s.eta, wait)) for s in stall.sources))
    held = replan(shop, jobs, base, now, stall, order=JOINT, deterministic=True)
    chosen = hold_or_roll_out(shop, jobs, base, now, stall, order=JOINT, deterministic=True)
    if held is None or chosen is None:
        return None
    validate(shop, jobs, held, now, base, stall)
    validate(shop, jobs, chosen, now, base, stall)
    h, c = metrics(jobs, held, base, now, stall), metrics(jobs, chosen, base, now, stall)
    return dict(rolled=chosen.info["bay"] == "roll_out", late_h=h["late"], late_c=c["late"], tard_h=h["tard"], tard_c=c["tard"],
                hold_h=h["hold"], hold_c=c["hold"])


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    os.makedirs(OUT, exist_ok=True)
    lines = [f"# When rolling the car out pays ({n} seeded days per setting)", "",
             "12 repair orders, 4 technicians, 1 flat bay; stalls where the car can be made movable.",
             "Averages per stall: always hold the bay, then let the engine choose. All data is synthetic.", "",
             "| Lift bays | Part at least | Stalls | Rolled out | Promises missed | Late minutes | Bay blocked (min) |",
             "|---|---|---|---|---|---|---|"]
    for n_lift in LIFT_BAYS:
        for wait in PART_AT_LEAST:
            with Pool(5) as pool:
                rows = [r for r in pool.map(one, [(s, n_lift, wait) for s in range(1, n + 1)]) if r]
            avg = lambda k: sum(r[k] for r in rows) / len(rows)
            away = "as generated" if wait == 0 else f"{wait // 60} h away"
            lines.append(f"| {n_lift} | {away} | {len(rows)} | {sum(r['rolled'] for r in rows)} | {avg('late_h'):.2f} to {avg('late_c'):.2f} | "
                         f"{avg('tard_h'):.1f} to {avg('tard_c'):.1f} | {avg('hold_h'):.0f} to {avg('hold_c'):.0f} |")
    lines += ["",
              "Reading: with three lift bays the next car nearly always finds another bay, so holding costs little and the",
              "engine almost never rolls a car out. With two lift bays, or when the part is hours away, rolling out keeps",
              "promises that holding the bay would lose. The roll-out and set-up minutes are assumptions (see shopgen.MOVABLE)."]
    text = "\n".join(lines)
    open(os.path.join(OUT, "roll_out_summary.md"), "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()

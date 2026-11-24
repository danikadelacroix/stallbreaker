"""StallBreaker benchmark: N seeded stalls, seven ways of responding, plus negative controls.

Run:  .venv/bin/python experiments/eval.py [N]
Writes experiments/out/eval_results.csv and eval_summary.md.
The shop is simulated (see shopgen.py), so these numbers show how the methods
compare on the simulator. They are not a forecast of savings at a real dealer.
"""
import csv
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shopcore import dispatch_edd, hold_or_roll_out, metrics, replan, right_shift, validate
from shopgen import make_day, make_stall

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
JOINT = ("late", "tard", "cost", "moves", "shift", "hold")
METHODS = ["wait, cheapest source", "wait, fastest source", "rule dispatch, fastest source",
           "solver, cheapest source fixed", "solver, fastest source fixed", "StallBreaker (joint)",
           "StallBreaker (joint, may roll the car out)"]


def one(seed):
    rng, shop, jobs, base = make_day(seed)
    if base is None:
        return None
    now, stall = make_stall(rng, jobs, base)
    if stall is None:
        return None
    safe = [s for s in stall.sources if s.safe]
    cheapest = min(safe, key=lambda s: (s.cost, s.eta))
    fastest = min(safe, key=lambda s: (s.eta, s.cost))
    plans = {
        METHODS[0]: right_shift(shop, jobs, base, now, stall, cheapest),
        METHODS[1]: right_shift(shop, jobs, base, now, stall, fastest),
        METHODS[2]: dispatch_edd(shop, jobs, base, now, stall, fastest),
        METHODS[3]: replan(shop, jobs, base, now, stall, force_source=cheapest.id, order=JOINT, workers=2),
        METHODS[4]: replan(shop, jobs, base, now, stall, force_source=fastest.id, order=JOINT, workers=2),
        METHODS[5]: replan(shop, jobs, base, now, stall, order=JOINT, workers=2),
        METHODS[6]: hold_or_roll_out(shop, jobs, base, now, stall, order=JOINT, workers=2),
    }
    rows = []
    by = {j.id: j for j in jobs}
    if any(p is None for p in plans.values()):
        raise RuntimeError(f"seed {seed}: a method found no feasible plan")
    for name, p in plans.items():
        validate(shop, jobs, p, now, base, stall)
        mt = metrics(jobs, p, base, now, stall)
        rows.append(dict(seed=seed, method=name, base_late=metrics(jobs, base)["late"], **mt,
                         movable=by[stall.job].roll_out is not None, rolled_out=p.info.get("bay") == "roll_out",
                         seconds=round(p.info["seconds"], 4), proven=p.info.get("proven", True),
                         picked_fastest=mt["source"] == fastest.id, picked_cheapest=mt["source"] == cheapest.id))
    # negative control: nothing is wrong, so the re-plan must not touch anything
    ctrl = replan(shop, jobs, base, now, order=("late", "tard", "moves", "shift"), workers=2)
    untouched = all(ctrl.assign[j.id] == base.assign[j.id] for j in jobs)
    return rows, untouched


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    os.makedirs(OUT, exist_ok=True)
    with Pool(5) as pool:
        res = pool.map(one, range(1, n + 1))
    res = [r for r in res if r]
    rows = [row for r in res for row in r[0]]
    controls_ok = sum(r[1] for r in res)
    with open(os.path.join(OUT, "eval_results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    lines = [f"# StallBreaker benchmark on the simulator ({len(res)} seeded stalls)", "",
             "12 repair orders, 4 technicians, 4 bays per day; one missing part per day; 4 candidate sources.",
             "All data is synthetic. Averages per stall.", "",
             "| Method | Promises missed | Late minutes | Bay blocked (min) | Jobs moved | Sourcing cost ($) | Max solve (s) |",
             "|---|---|---|---|---|---|---|"]
    for name in METHODS:
        r = [x for x in rows if x["method"] == name]
        avg = lambda k: sum(x[k] for x in r) / len(r)
        lines.append(f"| {name} | {avg('late'):.2f} | {avg('tard'):.1f} | {avg('hold'):.1f} | {avg('moved'):.2f} | "
                     f"{avg('cost'):.1f} | {max(x['seconds'] for x in r):.2f} |")
    j = [x for x in rows if x["method"] == METHODS[5]]
    lines += ["",
              f"- Morning plans with a missed promise before any stall: {sum(x['base_late'] > 0 for x in j)} of {len(j)}.",
              f"- Joint solves proven optimal within the time cap: {sum(x['proven'] for x in j)} of {len(j)}.",
              f"- Joint solver picked the fastest safe source in {sum(x['picked_fastest'] for x in j)} of {len(j)} stalls, "
              f"the cheapest safe source in {sum(x['picked_cheapest'] for x in j)}, and something in between in "
              f"{sum(not x['picked_fastest'] and not x['picked_cheapest'] for x in j)}.",
              f"- Negative controls (no stall, plan must stay untouched): {controls_ok} of {len(res)} passed.",
              f"- Every plan from every method passed the independent rule checker (validate)."]
    r7 = [x for x in rows if x["method"] == METHODS[6]]
    movable, rolled = [x for x in r7 if x["movable"]], [x for x in r7 if x["rolled_out"]]
    gain = lambda k: sum(a[k] - b[k] for a, b in zip(j, r7))
    lines += ["",
              f"- The stalled car could be made movable in {len(movable)} of {len(r7)} stalls (our assumption per job type). "
              f"The engine rolled it out in {len(rolled)} of those: only where that kept a promise, cut waiting or saved money.",
              f"- Over all {len(r7)} stalls, allowing a roll-out saved {gain('late')} missed promises, {gain('tard')} late minutes, "
              f"${gain('cost'):.0f} of sourcing cost and {gain('hold')} minutes of blocked bay in total."]
    text = "\n".join(lines)
    open(os.path.join(OUT, "eval_summary.md"), "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()

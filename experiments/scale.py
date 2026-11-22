"""Scale check: how long does a re-plan take on a bigger shop, and is the plan still proven optimal?

Run:  .venv/bin/python experiments/scale.py [days]
Writes experiments/out/scale_summary.md. Simulated shops; the solver is capped at 5 seconds per re-plan.
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shopcore import Bay, Shop, Tech, dispatch_edd, metrics, replan, validate
from shopgen import NAMES, SKILLSETS, make_jobs, make_stall

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
JOINT = ("late", "tard", "cost", "moves", "shift", "hold")
SIZES = [(12, 4, 3, 1), (24, 7, 5, 2), (40, 12, 9, 3), (60, 18, 13, 5)]  # jobs, technicians, lift bays, flat bays
CAP = 5.0


def big_shop(n_tech, n_lift, n_flat):
    techs = tuple(Tech(f"{NAMES[i % len(NAMES)]}-{i // len(NAMES) + 1}", frozenset(SKILLSETS[i % len(SKILLSETS)])) for i in range(n_tech))
    bays = tuple(Bay(f"Bay {i + 1}", "lift") for i in range(n_lift)) + tuple(Bay(f"Bay {n_lift + i + 1}", "flat") for i in range(n_flat))
    return Shop(techs, bays)


def one(seed, size):
    n_jobs, n_tech, n_lift, n_flat = size
    rng = random.Random(seed * 1000 + n_jobs)
    shop = big_shop(n_tech, n_lift, n_flat)
    jobs = make_jobs(rng, n_jobs)
    base = dispatch_edd(shop, jobs, None, 0)  # morning plan from the dispatch rule: fast at any size
    validate(shop, jobs, base)
    now, stall = make_stall(rng, jobs, base)
    if stall is None:
        return None
    t0 = time.perf_counter()
    plan = replan(shop, jobs, base, now, stall, order=JOINT, time_limit=CAP, workers=8)
    secs = time.perf_counter() - t0
    if plan is None:
        return dict(ok=False)
    validate(shop, jobs, plan, now, base, stall)
    safe = [s for s in stall.sources if s.safe]
    fastest = min(safe, key=lambda s: (s.eta, s.cost))
    rule = dispatch_edd(shop, jobs, base, now, stall, fastest)
    return dict(ok=True, secs=secs, proven=plan.info["proven"], late=metrics(jobs, plan)["late"], rule_late=metrics(jobs, rule)["late"],
                base_late=metrics(jobs, base)["late"])


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    lines = ["# Scale check (simulated shops, one stall per day, solver capped at 5 s)", "",
             "| Jobs | Technicians | Bays | Days | Median re-plan (s) | Slowest (s) | Proven optimal | Missed promises: solver / rule dispatch |",
             "|---|---|---|---|---|---|---|---|"]
    for size in SIZES:
        res = [r for r in (one(s, size) for s in range(1, days + 1)) if r and r["ok"]]
        secs = sorted(r["secs"] for r in res)
        lines.append(f"| {size[0]} | {size[1]} | {size[2] + size[3]} | {len(res)} | {secs[len(secs) // 2]:.2f} | {secs[-1]:.2f} | "
                     f"{sum(r['proven'] for r in res)} of {len(res)} | {sum(r['late'] for r in res)} / {sum(r['rule_late'] for r in res)} |")
        print(lines[-1], flush=True)
    lines += ["", "The morning plan here comes from the earliest-promise dispatch rule, not the solver, so some days start with missed promises.",
              "Every plan passed the rule checker. A plan that is not proven optimal within the cap is still valid; the engine flags it."]
    open(os.path.join(OUT, "scale_summary.md"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

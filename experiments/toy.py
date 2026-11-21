"""StallBreaker toy slice: 8 repair orders, 3 bays, 3 technicians, one missing part.

Run:  .venv/bin/python experiments/toy.py
Writes experiments/out/toy_before_after.png and prints the plans.
All shop data here is hand-made and synthetic.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shopcore import (Bay, Job, Shop, Source, Stall, Tech, clock, dispatch_edd, initial_plan, metrics,
                      replan, right_shift, tech_minutes, validate)
from shopviz import gantt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

SHOP = Shop(
    techs=(Tech("Meera", frozenset({"engine", "brakes", "general"})),
           Tech("Kavya", frozenset({"brakes", "general", "electrical"})),
           Tech("Riya", frozenset({"general", "electrical", "alignment"}))),
    bays=(Bay("Bay 1", "lift"), Bay("Bay 2", "lift"), Bay("Bay 3", "flat")),
)
L, F = ("lift",), ("flat",)
JOBS = [
    Job("RO-101", "Water pump replacement", 180, "engine", L, due=300, release=0),
    Job("RO-102", "Front brake pads", 90, "brakes", L, due=240, release=0),
    Job("RO-103", "Wheel alignment", 60, "alignment", F, due=180, release=0),
    Job("RO-104", "Oil service", 45, "general", L + F, due=260, release=60),
    Job("RO-105", "Timing belt", 150, "engine", L, due=510, release=120),
    Job("RO-106", "Battery and charging check", 75, "electrical", L + F, due=300, release=90),
    Job("RO-107", "Rotors and brake fluid", 120, "brakes", L, due=420, release=180),
    Job("RO-108", "AC service", 80, "general", L + F, due=450, release=240),
]
NOW = 150  # 10:30, the water pump job is torn down and the gasket kit turns out to be missing
SOURCES = (
    Source("north", "Sister store North (shuttle)", eta=40, cost=15, risk=0.62, safe=False),
    Source("vendor", "Local vendor (courier)", eta=60, cost=85, risk=0.0),
    Source("east", "Sister store East (shuttle)", eta=110, cost=15, risk=0.04),
    Source("oem", "OEM depot (next truck)", eta=240, cost=0, risk=0.0),
)
STALL = Stall("RO-101", "water pump gasket kit", SOURCES)
SRC = {s.id: s for s in SOURCES}


def show(title, plan, prev=None):
    by = {j.id: j for j in JOBS}
    print(f"\n{title}")
    for jid in sorted(plan.assign):
        a, j = plan.assign[jid], by[jid]
        flag = f"LATE {a.end - j.due}m" if a.end > j.due else ""
        chg = "moved" if prev and prev.assign[jid] != a and prev.assign[jid].start >= NOW else ""
        print(f"  {jid} {j.desc:28s} {clock(a.start)}-{clock(a.end)}  {a.tech:6s} {a.bay}  promise {clock(j.due)} {flag} {chg}")


def main():
    base = initial_plan(SHOP, JOBS)
    validate(SHOP, JOBS, base)
    show("MORNING PLAN (before the stall)", base)
    print("  metrics:", metrics(JOBS, base))

    runs = {}
    runs["A. No re-plan, cheapest source"] = right_shift(SHOP, JOBS, base, NOW, STALL, SRC["oem"])
    runs["B. No re-plan, fastest safe source"] = right_shift(SHOP, JOBS, base, NOW, STALL, SRC["vendor"])
    runs["C. Rule-based dispatch, fastest safe source"] = dispatch_edd(SHOP, JOBS, base, NOW, STALL, SRC["vendor"])
    runs["D. StallBreaker: keep promises"] = replan(SHOP, JOBS, base, NOW, STALL,
                                                    order=("late", "tard", "cost", "moves", "shift"), hours_bound=60)
    runs["E. StallBreaker: minimal change"] = replan(SHOP, JOBS, base, NOW, STALL,
                                                     order=("moves", "late", "tard", "cost", "shift"), hours_bound=60)
    runs["F. Manager forces the unsafe store (North)"] = replan(SHOP, JOBS, base, NOW, STALL, force_source="north",
                                                                 order=("late", "tard", "cost", "moves", "shift"), hours_bound=60)
    runs["G. Manager forces the free OEM truck"] = replan(SHOP, JOBS, base, NOW, STALL, force_source="oem",
                                                           order=("late", "tard", "cost", "moves", "shift"), hours_bound=60)

    print(f"\nSTALL at {clock(NOW)}: {STALL.job} is missing its {STALL.part}")
    print("  sources:")
    for s in SOURCES:
        print(f"    {s.name:32s} arrives {clock(NOW + s.eta)}  ${s.cost:<4.0f} donor stockout risk {s.risk:.0%}"
              f"{'  UNSAFE TO RAID' if not s.safe else ''}")
    print(f"\n{'option':46s} {'source':8s} {'late':>4s} {'late min':>8s} {'moved':>5s} {'bay blocked':>11s} {'cost':>6s} {'solve s':>8s}")
    for name, p in runs.items():
        validate(SHOP, JOBS, p, NOW, base, STALL)
        mt = metrics(JOBS, p, base, NOW, STALL)
        print(f"{name:46s} {mt['source']:8s} {mt['late']:4d} {mt['tard']:8d} {mt['moved']:5d} {mt['hold']:9d} m ${mt['cost']:5.0f} {p.info['seconds']:8.3f}")
    d = runs["D. StallBreaker: keep promises"]
    show("PLAN D (StallBreaker: keep promises)", d, base)
    print("  solver stages:", d.info["stages"], "| proven optimal:", d.info["proven"])
    hb, ha = tech_minutes(SHOP, base, NOW), tech_minutes(SHOP, d, NOW)
    print("  technician minutes still to work, before -> after:", {t: f"{hb[t]} -> {ha[t]}" for t in hb})

    # determinism check: same stall solved 5 times with a fixed seed
    sigs = set()
    for _ in range(5):
        p = replan(SHOP, JOBS, base, NOW, STALL, order=("late", "tard", "cost", "moves", "shift"), hours_bound=60)
        sigs.add(tuple(sorted((k, v.start, v.tech, v.bay) for k, v in p.assign.items())) + (p.source.id,))
    print(f"\n  repeatability: 5 solves of the same stall gave {len(sigs)} distinct plan(s)")

    a = runs["A. No re-plan, cheapest source"]
    ma, md = metrics(JOBS, a, base, NOW, STALL), metrics(JOBS, d, base, NOW, STALL)
    path = gantt(SHOP, JOBS, [
        ("Morning plan: every promise time met", base, None),
        (f"10:30 stall on RO-101, no re-plan (wait for the free OEM truck): {ma['late']} promises missed, "
         f"bay blocked {ma['hold']} min", a, base),
        (f"StallBreaker re-plan in {d.info['seconds']:.2f}s, part from {d.source.name}: {md['late']} promises missed, "
         f"{md['moved']} jobs moved, bay blocked {md['hold']} min", d, base),
    ], NOW, os.path.join(OUT, "toy_before_after.png"))
    print("\n  chart:", os.path.relpath(path, os.path.dirname(OUT)))


if __name__ == "__main__":
    main()

"""Checks on the re-planning engine. Run:  .venv/bin/python -m pytest -q"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments"))

from shopcore import dispatch_edd, initial_plan, metrics, replan, right_shift, validate
from shopgen import make_day, make_stall
import toy

KEEP = ("late", "tard", "cost", "moves", "shift")


def test_morning_plan_keeps_every_promise():
    base = initial_plan(toy.SHOP, toy.JOBS)
    assert validate(toy.SHOP, toy.JOBS, base)
    assert metrics(toy.JOBS, base)["late"] == 0


def test_toy_stall_is_repaired_without_missing_a_promise():
    base = initial_plan(toy.SHOP, toy.JOBS)
    plan = replan(toy.SHOP, toy.JOBS, base, toy.NOW, toy.STALL, order=KEEP, hours_bound=60)
    assert validate(toy.SHOP, toy.JOBS, plan, toy.NOW, base, toy.STALL)
    assert plan.info["proven"]
    assert metrics(toy.JOBS, plan, base, toy.NOW, toy.STALL)["late"] == 0
    assert plan.source.safe, "must not raid a store that would run out"
    assert plan.source.id == "east", "cheapest source that still keeps every promise"


def test_unsafe_source_is_never_picked_unless_forced():
    base = initial_plan(toy.SHOP, toy.JOBS)
    free = replan(toy.SHOP, toy.JOBS, base, toy.NOW, toy.STALL, order=KEEP)
    forced = replan(toy.SHOP, toy.JOBS, base, toy.NOW, toy.STALL, order=KEEP, force_source="north")
    assert free.source.id != "north"
    assert forced.source.id == "north"


def test_work_resumes_only_after_the_part_arrives_and_in_the_same_bay():
    base = initial_plan(toy.SHOP, toy.JOBS)
    for src in toy.SOURCES:
        plan = replan(toy.SHOP, toy.JOBS, base, toy.NOW, toy.STALL, order=KEEP, force_source=src.id)
        a = plan.assign[toy.STALL.job]
        assert a.start >= toy.NOW + src.eta
        assert a.bay == base.assign[toy.STALL.job].bay


def test_nothing_wrong_means_nothing_moves():
    for seed in range(1, 9):
        _, shop, jobs, base = make_day(seed)
        plan = replan(shop, jobs, base, 150, order=("late", "tard", "moves", "shift"), workers=2)
        assert all(plan.assign[j.id] == base.assign[j.id] for j in jobs)


def test_solver_never_loses_to_the_baselines_on_missed_promises():
    for seed in range(1, 13):
        rng, shop, jobs, base = make_day(seed)
        now, stall = make_stall(rng, jobs, base)
        if stall is None:
            continue
        safe = [s for s in stall.sources if s.safe]
        fastest = min(safe, key=lambda s: (s.eta, s.cost))
        joint = replan(shop, jobs, base, now, stall, order=KEEP, workers=2)
        validate(shop, jobs, joint, now, base, stall)
        for other in (right_shift(shop, jobs, base, now, stall, fastest), dispatch_edd(shop, jobs, base, now, stall, fastest)):
            validate(shop, jobs, other, now, base, stall)
            assert metrics(jobs, joint)["late"] <= metrics(jobs, other)["late"]


def test_same_stall_gives_the_same_plan():
    base = initial_plan(toy.SHOP, toy.JOBS)
    seen = set()
    for _ in range(3):
        p = replan(toy.SHOP, toy.JOBS, base, toy.NOW, toy.STALL, order=KEEP, hours_bound=60)
        seen.add(tuple(sorted((k, v.start, v.tech, v.bay) for k, v in p.assign.items())) + (p.source.id,))
    assert len(seen) == 1


def test_a_job_not_yet_started_waits_for_its_part():
    base = initial_plan(toy.SHOP, toy.JOBS)
    later = [j for j in toy.JOBS if base.assign[j.id].start > toy.NOW][0]
    from shopcore import Stall
    stall = Stall(later.id, "part", toy.SOURCES)
    plan = replan(toy.SHOP, toy.JOBS, base, toy.NOW, stall, order=KEEP)
    assert validate(toy.SHOP, toy.JOBS, plan, toy.NOW, base, stall)
    a = plan.assign[later.id]
    assert a.start >= toy.NOW + plan.source.eta
    assert a.end - a.start == later.dur, "an unstarted job is not split"
    assert plan.hold == 0 and plan.extra == [], "no bay is blocked when the car has not been touched"


def test_pinned_jobs_and_blocked_bays_are_respected():
    base = initial_plan(toy.SHOP, toy.JOBS)
    future = sorted((j for j in toy.JOBS if base.assign[j.id].start > toy.NOW), key=lambda j: base.assign[j.id].start)
    pin = future[-1].id
    blocked_bay = base.assign[toy.STALL.job].bay
    block = (blocked_bay, toy.NOW, toy.NOW + 300)
    others = [j for j in toy.JOBS if j.id != toy.STALL.job]
    prev = type(base)(assign={k: v for k, v in base.assign.items() if k != toy.STALL.job})
    plan = replan(toy.SHOP, others, prev, toy.NOW, order=("late", "tard", "moves", "shift"), pinned=frozenset({pin}), blocks=(block,))
    assert validate(toy.SHOP, others, plan, toy.NOW, prev, pinned=frozenset({pin}), blocks=(block,))
    assert plan.assign[pin] == prev.assign[pin]
    for jid, a in plan.assign.items():
        if a.bay == blocked_bay and a.start >= toy.NOW:
            assert a.start >= toy.NOW + 300 or jid == pin

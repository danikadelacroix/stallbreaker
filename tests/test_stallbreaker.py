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

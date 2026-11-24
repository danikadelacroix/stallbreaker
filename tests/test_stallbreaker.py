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


# --- spec 109: hold the bay, or roll the car out? ---

from dataclasses import replace  # noqa: E402

from shopcore import Assign, Bay, Job, Plan, Shop, Source, Stall, Tech, hold_or_roll_out  # noqa: E402

ONE_LIFT = Shop((Tech("Asha", frozenset({"brakes"})), Tech("Bela", frozenset({"brakes"}))), (Bay("Bay 1", "lift"),))
TWO_LIFTS = Shop(ONE_LIFT.techs, (Bay("Bay 1", "lift"), Bay("Bay 2", "lift")))
PART = (Source("depot", "OEM depot", eta=180, cost=0),)


def _brake_day(shop, movable, next_due=260):
    """At 09:00 the first car is an hour into a two-hour brake job when a part turns out to be missing.
    The second car is booked for the same bay straight after it."""
    first = Job("RO-1", "Front brake pads", 120, "brakes", ("lift",), due=600, roll_out=20 if movable else None, set_up=15)
    second = Job("RO-2", "Front brake pads", 90, "brakes", ("lift",), due=next_due)
    prev = Plan(assign={"RO-1": Assign(0, 120, "Asha", "Bay 1"), "RO-2": Assign(120, 210, "Bela", shop.bays[-1].id)})
    return [first, second], prev, 60, Stall("RO-1", "pads", PART)


def test_a_car_that_cannot_be_moved_is_always_held():
    jobs, prev, now, stall = _brake_day(ONE_LIFT, movable=False)
    plan = hold_or_roll_out(ONE_LIFT, jobs, prev, now, stall, order=KEEP)
    assert validate(ONE_LIFT, jobs, plan, now, prev, stall)
    assert plan.info["bay"] == "hold" and plan.info["bay_why"] == "cannot_move"
    assert plan.hold == 180 and plan.assign["RO-1"].bay == "Bay 1"
    assert metrics(jobs, plan, prev, now, stall)["late"] == 1, "the next car waits behind the blocked bay and misses its promise"


def test_rolling_the_car_out_frees_the_bay_when_that_saves_a_promise():
    jobs, prev, now, stall = _brake_day(ONE_LIFT, movable=True)
    plan = hold_or_roll_out(ONE_LIFT, jobs, prev, now, stall, order=KEEP)
    assert validate(ONE_LIFT, jobs, plan, now, prev, stall)
    assert plan.info["bay"] == "roll_out" and plan.info["rolled_out_until"] == now + 20
    assert plan.hold == 0, "nothing sits in the bay waiting"
    assert metrics(jobs, plan, prev, now, stall)["late"] == 0
    assert plan.info["other"]["late"] == 1, "it also says what holding the bay would have cost"
    rest = plan.assign["RO-1"]
    assert rest.start >= now + 180, "the remaining work still waits for the part"
    assert rest.end - rest.start == 60 + 15, "the remaining hour, plus the time to set the car up again"
    second = plan.assign["RO-2"]
    assert second.start >= now + 20, "the bay is free only once the car has been rolled out"
    assert second.tech != "Asha" or second.start >= now + 20, "the technician rolling the car out is busy until then"


def test_the_car_stays_put_when_rolling_it_out_would_help_nobody():
    jobs, prev, now, stall = _brake_day(TWO_LIFTS, movable=True)
    plan = hold_or_roll_out(TWO_LIFTS, jobs, prev, now, stall, order=KEEP)
    assert validate(TWO_LIFTS, jobs, plan, now, prev, stall)
    assert plan.info["bay"] == "hold" and plan.info["bay_why"] == "no_gain"
    assert plan.assign["RO-1"].bay == "Bay 1" and plan.hold == 180


def test_without_movable_cars_the_decision_changes_nothing():
    base = initial_plan(toy.SHOP, toy.JOBS)
    plain = replan(toy.SHOP, toy.JOBS, base, toy.NOW, toy.STALL, order=KEEP, deterministic=True)
    decided = hold_or_roll_out(toy.SHOP, toy.JOBS, base, toy.NOW, toy.STALL, order=KEEP, deterministic=True)
    assert decided.assign == plain.assign and decided.source == plain.source and decided.hold == plain.hold


def test_the_checker_catches_a_rolled_out_car_that_was_never_really_moved():
    jobs, prev, now, stall = _brake_day(ONE_LIFT, movable=True)
    plan = hold_or_roll_out(ONE_LIFT, jobs, prev, now, stall, order=KEEP)
    cheat = replace(plan.assign["RO-2"], start=now, end=now + 90, tech="Bela")  # uses the bay while the car is still in it
    bad = Plan(assign={**plan.assign, "RO-2": cheat}, extra=plan.extra, source=plan.source, info=plan.info)
    try:
        validate(ONE_LIFT, jobs, bad, now, prev, stall)
    except AssertionError:
        return
    raise AssertionError("the checker accepted a job in a bay that was still occupied")


def test_a_car_is_not_rolled_out_just_to_move_fewer_jobs():
    """Rolling a car out costs technician time, so it must earn it: a kept promise, less waiting, or money.
    Here holding the bay only pushes the next car back by an hour, still well inside its promise."""
    jobs, prev, now, stall = _brake_day(ONE_LIFT, movable=True, next_due=900)
    plan = hold_or_roll_out(ONE_LIFT, jobs, prev, now, stall, order=("moves", "late", "tard", "cost", "shift"))
    assert validate(ONE_LIFT, jobs, plan, now, prev, stall)
    assert plan.info["bay"] == "hold" and plan.info["bay_why"] == "no_gain"

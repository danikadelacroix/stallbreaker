"""shopcore: a small service-shop re-planning engine on Google OR-Tools CP-SAT.

Time is minutes from 08:00. Everything here runs on synthetic shop data.

Method notes
 - The model follows the pattern of Google's flexible job-shop example
   (optional interval per alternative resource, exactly-one choice, no-overlap):
   https://github.com/google/or-tools/blob/stable/examples/python/flexible_job_shop_sat.py
 - Each job needs one technician (with the right skill) AND one bay (of the right
   kind) for its whole duration.
 - A stalled job keeps its bay (the car is dismantled) but frees its technician
   until the part arrives. Where the part comes from is a decision variable in the
   same model as the schedule.
 - Objectives are solved lexicographically, e.g. fewest broken promises, then
   least lateness, then fewest moved jobs, then lowest sourcing cost.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ortools.sat.python import cp_model

H = 1080  # planning horizon in minutes from 08:00; finishing after a promise time counts as late
INF = 10**9


@dataclass(frozen=True)
class Tech:
    id: str
    skills: frozenset


@dataclass(frozen=True)
class Bay:
    id: str
    kind: str


@dataclass(frozen=True)
class Shop:
    techs: tuple
    bays: tuple


@dataclass(frozen=True)
class Job:
    id: str
    desc: str
    dur: int
    skill: str
    bay_kinds: tuple
    due: int  # promise time
    release: int = 0  # earliest start (car arrival / parts ready)


@dataclass(frozen=True)
class Assign:
    start: int
    end: int
    tech: str
    bay: str


@dataclass(frozen=True)
class Seg:  # extra drawing segment for a stalled job
    job: str
    start: int
    end: int
    tech: Optional[str]
    bay: str
    kind: str  # 'done' (work before the stall) | 'hold' (bay blocked, waiting for part)


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    eta: int  # minutes until the part is at the bay
    cost: float  # extra sourcing cost in dollars
    risk: float = 0.0  # chance the giving store runs out if it lends the part
    safe: bool = True


@dataclass(frozen=True)
class Stall:
    job: str
    part: str
    sources: tuple


@dataclass
class Plan:
    assign: dict  # job id -> Assign (for a stalled job: the remaining work)
    extra: list = field(default_factory=list)
    source: Optional[Source] = None
    hold: int = 0  # minutes the bay sits blocked with nobody working
    info: dict = field(default_factory=dict)


def clock(m: int) -> str:
    return f"{8 + m // 60:02d}:{m % 60:02d}"


def _stall_in_progress(prev, now, stall):
    """True when the stalled job has already been started, so the car is dismantled in its bay.
    A stalled job that has not started yet simply cannot begin before its part arrives."""
    if not stall or not prev or stall.job not in prev.assign:
        return False
    a = prev.assign[stall.job]
    return a.start <= now < a.end


def _split(jobs, prev, now, stall, pinned=frozenset()):
    """Sort jobs into done, fixed (running or pinned) and free to re-plan."""
    done, running, todo = [], [], []
    in_progress = _stall_in_progress(prev, now, stall)
    for j in jobs:
        a = prev.assign.get(j.id) if prev else None
        if in_progress and j.id == stall.job:
            continue
        if a and a.end <= now:
            done.append(j)
        elif a and (a.start < now or j.id in pinned):
            running.append(j)
        else:
            todo.append(j)
    return done, running, todo


def _elig(shop, j):
    ts = [t.id for t in shop.techs if j.skill in t.skills]
    bs = [b.id for b in shop.bays if b.kind in j.bay_kinds]
    return ts, bs


def replan(shop, jobs, prev, now, stall=None, force_source=None, allow_unsafe=False,
           order=("late", "tard", "moves", "cost", "shift"), time_limit=5.0,
           hours_bound=None, workers=8, seed=7, deterministic=False, pinned=frozenset(), blocks=()):
    """Re-plan everything not yet started. Returns a Plan, or None if infeasible.

    pinned: ids of jobs whose current assignment must not change (for example the rest of an
            earlier stalled job). blocks: (bay, start, end) periods when a bay is unavailable."""
    t0 = time.perf_counter()
    m = cp_model.CpModel()
    by = {j.id: j for j in jobs}
    tech_iv = {t.id: [] for t in shop.techs}
    bay_iv = {b.id: [] for b in shop.bays}
    done, running, todo = _split(jobs, prev, now, stall, pinned)
    in_progress = _stall_in_progress(prev, now, stall)
    out = {}
    c_late = c_tard = 0
    hours_before = {t.id: 0 for t in shop.techs}
    hours_fixed = {t.id: 0 for t in shop.techs}

    for j in done:
        a = prev.assign[j.id]
        out[j.id] = a
        c_late += a.end > j.due
        c_tard += max(0, a.end - j.due)
    for j in running:
        a = prev.assign[j.id]
        out[j.id] = a
        c_late += a.end > j.due
        c_tard += max(0, a.end - j.due)
        tech_iv[a.tech].append(m.new_interval_var(a.start, a.end - a.start, a.end, f"run_t_{j.id}"))
        bay_iv[a.bay].append(m.new_interval_var(a.start, a.end - a.start, a.end, f"run_b_{j.id}"))
        hours_before[a.tech] += a.end - max(a.start, now)
        hours_fixed[a.tech] += a.end - max(a.start, now)
    for bay, b_start, b_end in blocks:
        if b_end > now and bay in bay_iv:
            bay_iv[bay].append(m.new_interval_var(b_start, b_end - b_start, b_end, f"block_{bay}_{b_start}"))

    # Where the part comes from is a decision variable, whether or not the job has started.
    z, eta_expr, cost_expr = None, 0, 0
    if stall:
        z = {k.id: m.new_bool_var(f"z_{k.id}") for k in stall.sources}
        m.add_exactly_one(z.values())
        for k in stall.sources:
            if force_source:
                m.add(z[k.id] == int(k.id == force_source))
            elif not k.safe and not allow_unsafe:
                m.add(z[k.id] == 0)
        eta_expr = sum(z[k.id] * k.eta for k in stall.sources)
        cost_expr = sum(z[k.id] * int(round(k.cost)) for k in stall.sources)

    V = {}  # job id -> dict of vars
    late_v, tard_v, moved_v, shift_v, end_v = [], [], [], [], []
    hours_after = {t.id: [] for t in shop.techs}
    hints = []
    for j in todo:
        a = prev.assign.get(j.id) if prev else None
        lb = max(now, j.release)
        s = m.new_int_var(lb, H - j.dur, f"s_{j.id}")
        ts, bs = _elig(shop, j)
        if not ts or not bs:
            raise ValueError(f"{j.id}: no eligible technician or bay")
        xt, yb = {}, {}
        for t in ts:
            xt[t] = m.new_bool_var(f"x_{j.id}_{t}")
            tech_iv[t].append(m.new_optional_interval_var(s, j.dur, s + j.dur, xt[t], f"it_{j.id}_{t}"))
            hours_after[t].append(xt[t] * j.dur)
        for b in bs:
            yb[b] = m.new_bool_var(f"y_{j.id}_{b}")
            bay_iv[b].append(m.new_optional_interval_var(s, j.dur, s + j.dur, yb[b], f"ib_{j.id}_{b}"))
        m.add_exactly_one(xt.values())
        m.add_exactly_one(yb.values())
        if stall and j.id == stall.job:
            m.add(s >= now + eta_expr)  # not started yet: it just cannot begin before the part arrives
        tard = m.new_int_var(0, H, f"tard_{j.id}")
        m.add(tard >= s + j.dur - j.due)
        late = m.new_bool_var(f"late_{j.id}")
        m.add(s + j.dur <= j.due).only_enforce_if(late.Not())
        late_v.append(late)
        tard_v.append(tard)
        end_v.append(s + j.dur)
        if a:
            hours_before[a.tech] += a.end - a.start
            moved = m.new_bool_var(f"moved_{j.id}")
            same = m.new_bool_var(f"same_{j.id}")
            m.add(s == a.start).only_enforce_if(same)
            m.add_bool_or([moved, same])
            if a.tech in xt:
                m.add_bool_or([moved, xt[a.tech]])
            else:
                m.add(moved == 1)
            if a.bay in yb:
                m.add_bool_or([moved, yb[a.bay]])
            else:
                m.add(moved == 1)
            d = m.new_int_var(0, H, f"d_{j.id}")
            m.add_abs_equality(d, s - a.start)
            moved_v.append(moved)
            shift_v.append(d)
            if a.start >= lb:
                hints.append((s, a.start))
                for t in xt:
                    hints.append((xt[t], int(t == a.tech)))
                for b in yb:
                    hints.append((yb[b], int(b == a.bay)))
        V[j.id] = dict(s=s, xt=xt, yb=yb)

    hold_expr = 0
    st = None
    if stall and in_progress:
        j = by[stall.job]
        a = prev.assign[j.id]
        rem = a.end - now
        rs = m.new_int_var(now, H - rem, "rs")
        m.add(rs >= now + eta_expr)
        hold = m.new_int_var(rem, H, "hold_size")
        m.add(hold == rs + rem - now)
        bay_iv[a.bay].append(m.new_interval_var(now, hold, rs + rem, "hold"))  # bay stays blocked
        ts, _ = _elig(shop, j)
        xr = {}
        for t in ts:
            xr[t] = m.new_bool_var(f"xr_{t}")
            tech_iv[t].append(m.new_optional_interval_var(rs, rem, rs + rem, xr[t], f"ir_{t}"))
            hours_after[t].append(xr[t] * rem)
        m.add_exactly_one(xr.values())
        tard = m.new_int_var(0, H, "tard_stall")
        m.add(tard >= rs + rem - j.due)
        late = m.new_bool_var("late_stall")
        m.add(rs + rem <= j.due).only_enforce_if(late.Not())
        late_v.append(late)
        tard_v.append(tard)
        end_v.append(rs + rem)
        hold_expr = rs - now
        hours_before[a.tech] += rem
        st = dict(a=a, rem=rem, rs=rs, xr=xr)

    for t in tech_iv:
        m.add_no_overlap(tech_iv[t])
    for b in bay_iv:
        m.add_no_overlap(bay_iv[b])
    if hours_bound is not None:
        for t in hours_after:
            m.add(hours_fixed[t] + sum(hours_after[t]) >= hours_before[t] - hours_bound)

    terms = {
        "late": sum(late_v) + c_late,
        "tard": sum(tard_v) + c_tard,
        "moves": sum(moved_v) if moved_v else 0,
        "shift": sum(shift_v) if shift_v else 0,
        "cost": cost_expr,
        "hold": hold_expr,
        "sumend": sum(end_v) if end_v else 0,
    }
    for var, val in hints:
        m.add_hint(var, val)

    solver = cp_model.CpSolver()
    stages = []
    per_stage = time_limit / max(1, len(order))
    for i, key in enumerate(order):
        expr = terms[key]
        if isinstance(expr, int):
            stages.append((key, expr, "CONST"))
            continue
        m.minimize(expr)
        solver = cp_model.CpSolver()
        if deterministic:  # same answer on every run and every machine
            solver.parameters.max_deterministic_time = per_stage
            solver.parameters.num_workers = 1
        else:
            solver.parameters.max_time_in_seconds = per_stage
            solver.parameters.num_workers = workers
        solver.parameters.random_seed = seed
        status = solver.solve(m)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        val = int(round(solver.objective_value))
        stages.append((key, val, solver.status_name(status)))
        m.add(expr <= val)
        m.clear_hints()
        for jid, v in V.items():
            m.add_hint(v["s"], solver.value(v["s"]))
            for b_ in list(v["xt"].values()) + list(v["yb"].values()):
                m.add_hint(b_, solver.value(b_))
        if z:
            for b_ in z.values():
                m.add_hint(b_, solver.value(b_))
        if st:
            m.add_hint(st["rs"], solver.value(st["rs"]))
            for b_ in st["xr"].values():
                m.add_hint(b_, solver.value(b_))

    for jid, v in V.items():
        s = solver.value(v["s"])
        t = next(t for t, b in v["xt"].items() if solver.value(b))
        b = next(b for b, y in v["yb"].items() if solver.value(y))
        out[jid] = Assign(s, s + by[jid].dur, t, b)
    plan = Plan(assign=out)
    if z:
        plan.source = next(k for k in stall.sources if solver.value(z[k.id]))
    if st:
        a, rem = st["a"], st["rem"]
        rs = solver.value(st["rs"])
        t = next(t for t, b in st["xr"].items() if solver.value(b))
        out[stall.job] = Assign(rs, rs + rem, t, a.bay)
        plan.extra = [Seg(stall.job, a.start, now, a.tech, a.bay, "done")]
        if rs > now:
            plan.extra.append(Seg(stall.job, now, rs, None, a.bay, "hold"))
        plan.hold = rs - now
    plan.info = dict(stages=stages, seconds=time.perf_counter() - t0,
                     proven=all(s[2] in ("OPTIMAL", "CONST") for s in stages), method="cp-sat")
    return plan


def _baseline_start(shop, jobs, prev, now, stall, pinned=frozenset()):
    done, running, todo = _split(jobs, prev, now, stall, pinned)
    out = {}
    tech_free = {t.id: now for t in shop.techs}
    bay_free = {b.id: now for b in shop.bays}
    for j in done:
        out[j.id] = prev.assign[j.id]
    for j in running:
        a = prev.assign[j.id]
        out[j.id] = a
        tech_free[a.tech] = max(tech_free[a.tech], a.end)
        bay_free[a.bay] = max(bay_free[a.bay], a.end)
    return out, tech_free, bay_free, todo


def right_shift(shop, jobs, prev, now, stall=None, source=None, pinned=frozenset()):
    """'No re-plan' baseline: same technician, bay and order for every job; things
    only slide later. A stalled technician waits at the car for the part. New jobs
    go to the back of the queue."""
    t0 = time.perf_counter()
    by = {j.id: j for j in jobs}
    out, tech_free, bay_free, todo = _baseline_start(shop, jobs, prev, now, stall, pinned)
    plan = Plan(assign=out)
    if stall:
        a = prev.assign[stall.job]
        rem = a.end - now
        rs = now + source.eta
        out[stall.job] = Assign(rs, rs + rem, a.tech, a.bay)
        tech_free[a.tech] = bay_free[a.bay] = rs + rem
        plan.extra = [Seg(stall.job, a.start, now, a.tech, a.bay, "done"),
                      Seg(stall.job, now, rs, None, a.bay, "hold")]
        plan.source, plan.hold = source, rs - now
    key = lambda j: (prev.assign[j.id].start if prev and j.id in prev.assign else INF, j.release, j.id)
    for j in sorted(todo, key=key):
        a = prev.assign.get(j.id) if prev else None
        if a:
            t, b = a.tech, a.bay
            s = max(a.start, j.release, now, tech_free[t], bay_free[b])
        else:
            ts, bs = _elig(shop, j)
            s, t, b = min((max(now, j.release, tech_free[t], bay_free[b]), t, b) for t in ts for b in bs)
        out[j.id] = Assign(s, s + j.dur, t, b)
        tech_free[t] = bay_free[b] = s + j.dur
    plan.info = dict(seconds=time.perf_counter() - t0, method="right-shift")
    return plan


def dispatch_edd(shop, jobs, prev, now, stall=None, source=None, pinned=frozenset()):
    """Rule-based dispatch baseline: whenever a technician and a suitable bay are
    free, start the waiting job with the earliest promise time. With a stall, the
    technician is released and the remaining work re-enters the queue when the
    part arrives."""
    t0 = time.perf_counter()
    by = {j.id: j for j in jobs}
    out, tech_free, bay_free, todo = _baseline_start(shop, jobs, prev, now, stall, pinned)
    plan = Plan(assign=out)
    pend = []
    for j in todo:
        ts, bs = _elig(shop, j)
        a = prev.assign.get(j.id) if prev else None
        pend.append(dict(id=j.id, dur=j.dur, ts=ts, bs=bs, rel=max(now, j.release), due=j.due, a=a, rem=False))
    held = None
    if stall:
        j = by[stall.job]
        a = prev.assign[j.id]
        rem = a.end - now
        ts, _ = _elig(shop, j)
        held = a.bay
        bay_free[held] = INF
        pend.append(dict(id=j.id, dur=rem, ts=ts, bs=[held], rel=now + source.eta, due=j.due, a=a, rem=True))
        plan.extra = [Seg(j.id, a.start, now, a.tech, a.bay, "done")]
        plan.source = source
    t = now
    guard = 0
    while pend:
        guard += 1
        if guard > 10000:
            raise RuntimeError("dispatch deadlock")
        placed = True
        while placed:
            placed = False
            for p in sorted(pend, key=lambda p: (p["due"], p["id"])):
                if p["rel"] > t:
                    continue
                ts = [x for x in p["ts"] if tech_free[x] <= t]
                bs = [b for b in p["bs"] if bay_free[b] <= t or (p["rem"] and b == held)]
                if ts and bs:
                    a = p["a"]
                    tt = a.tech if a and a.tech in ts else ts[0]
                    bb = a.bay if a and a.bay in bs else bs[0]
                    out[p["id"]] = Assign(t, t + p["dur"], tt, bb)
                    tech_free[tt] = bay_free[bb] = t + p["dur"]
                    if p["rem"]:
                        plan.hold = t - now
                        if t > now:
                            plan.extra.append(Seg(p["id"], now, t, None, bb, "hold"))
                    pend.remove(p)
                    placed = True
                    break
        if pend:
            nxt = [x for x in list(tech_free.values()) + list(bay_free.values()) + [p["rel"] for p in pend]
                   if t < x < INF]
            t = min(nxt)
    plan.info = dict(seconds=time.perf_counter() - t0, method="edd-dispatch")
    return plan


def validate(shop, jobs, plan, now=0, prev=None, stall=None, pinned=frozenset(), blocks=()):
    """Independent checker: raises AssertionError if a plan breaks any rule."""
    in_progress = _stall_in_progress(prev, now, stall)
    by = {j.id: j for j in jobs}
    techs = {t.id: t for t in shop.techs}
    bays = {b.id: b for b in shop.bays}
    assert set(plan.assign) == set(by), "every job must be planned exactly once"
    tsegs = {t: [] for t in techs}
    bsegs = {b: [] for b in bays}
    for jid, a in plan.assign.items():
        j = by[jid]
        assert j.skill in techs[a.tech].skills, f"{jid}: technician lacks skill"
        assert bays[a.bay].kind in j.bay_kinds, f"{jid}: wrong bay kind"
        is_stalled = in_progress and jid == stall.job
        if jid in pinned and prev is not None and jid in prev.assign:
            assert a == prev.assign[jid], f"{jid}: pinned job was changed"
        elif not is_stalled:
            assert a.end - a.start == j.dur, f"{jid}: wrong duration"
            assert a.start >= j.release, f"{jid}: starts before release"
        if prev is not None and jid in prev.assign and not is_stalled and prev.assign[jid].start < now:
            assert a == prev.assign[jid], f"{jid}: started work was changed"
        elif a.start < now and not (prev is not None and jid in prev.assign):
            raise AssertionError(f"{jid}: new job planned in the past")
        tsegs[a.tech].append((a.start, a.end, jid))
        bsegs[a.bay].append((a.start, a.end, jid))
    for s in plan.extra:
        if s.kind == "hold":
            bsegs[s.bay].append((s.start, s.end, s.job + "(hold)"))
        if s.kind == "done":
            tsegs[s.tech].append((s.start, s.end, s.job + "(done)"))
            bsegs[s.bay].append((s.start, s.end, s.job + "(done)"))
    for bay, b_start, b_end in blocks:
        if b_end > now:
            bsegs[bay].append((b_start, b_end, "(blocked)"))
    if stall:
        a = plan.assign[stall.job]
        assert plan.source is not None and a.start >= now + plan.source.eta, "work starts before the part arrives"
        if in_progress:
            assert a.bay == prev.assign[stall.job].bay, "dismantled car changed bay"
    for name, d in (("technician", tsegs), ("bay", bsegs)):
        for r, segs in d.items():
            segs.sort()
            for (s1, e1, j1), (s2, e2, j2) in zip(segs, segs[1:]):
                assert e1 <= s2, f"{name} {r}: {j1} overlaps {j2}"
    return True


def metrics(jobs, plan, prev=None, now=0, stall=None):
    late = tard = moved = 0
    for j in jobs:
        a = plan.assign[j.id]
        late += a.end > j.due
        tard += max(0, a.end - j.due)
        if prev is not None and j.id in prev.assign and not (stall and j.id == stall.job):
            p = prev.assign[j.id]
            if p.start >= now and p != a:
                moved += 1
    return dict(late=late, tard=tard, moved=moved, hold=plan.hold,
                cost=plan.source.cost if plan.source else 0.0,
                source=plan.source.id if plan.source else None)


def tech_minutes(shop, plan, now=0):
    out = {t.id: 0 for t in shop.techs}
    for a in plan.assign.values():
        out[a.tech] += max(0, a.end - max(a.start, now))
    return out


def initial_plan(shop, jobs, time_limit=3.0, deterministic=False):
    """The morning plan: fewest late jobs, least lateness, then finish early."""
    return replan(shop, jobs, None, 0, order=("late", "tard", "sumend"), time_limit=time_limit,
                  deterministic=deterministic)

"""The stall flow: a part is missing (or running late), the engine proposes plans, a manager approves one."""
import json
import os
import sys
from dataclasses import replace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from shopcore import Assign, Plan, Source, Stall, metrics, replan, right_shift, validate  # noqa: E402

from . import db, repo, sourcing  # noqa: E402

OPTIONS = [
    ("keep_promises", "Fewest missed promises", ("late", "tard", "cost", "moves", "shift", "hold")),
    ("fewest_moves", "Fewest jobs moved", ("moves", "late", "tard", "cost", "shift", "hold")),
]
SOLVE_SECONDS = 4.0


class StallError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


def _as_dict(a):
    return {"start_min": a.start, "end_min": a.end, "technician": a.tech, "bay": a.bay}


def _solve(conn, shop, jobs, live, prev, now, stall, pinned, blocks, force_source=None):
    """Ask the engine for each kind of plan. 'live' is the plan on the board, used to list what would move;
    'prev' is what the engine re-plans from (the same, except when a waiting job is being re-timed)."""
    ro_id = stall.job
    info = {r["id"]: r for r in conn.execute("SELECT id, vehicle, promise_min FROM repair_orders")}
    options = []
    for key, title, goal_order in OPTIONS:
        p = replan(shop, jobs, prev, now, stall, force_source=force_source, order=goal_order, time_limit=SOLVE_SECONDS, pinned=pinned, blocks=blocks)
        if p is None:
            continue
        validate(shop, jobs, p, now, prev, stall, pinned, blocks)
        m = metrics(jobs, p, live, now, stall)
        changes = [{"ro_id": j.id, "description": j.desc, "before": _as_dict(live.assign[j.id]), "after": _as_dict(p.assign[j.id])}
                   for j in jobs if j.id != ro_id and live.assign[j.id].start >= now and p.assign[j.id] != live.assign[j.id]]
        late = [{"ro_id": j.id, "vehicle": info[j.id]["vehicle"], "description": j.desc, "promise_min": j.due, "end_min": p.assign[j.id].end,
                 "late_before": live.assign[j.id].end > j.due} for j in jobs if p.assign[j.id].end > j.due]
        options.append({
            "key": key, "title": title, "source_id": p.source.id, "source_name": p.source.name,
            "arrives_min": now + p.source.eta, "cost": p.source.cost,
            "missed_promises": m["late"], "late_minutes": m["tard"], "jobs_moved": m["moved"], "bay_blocked_min": p.hold,
            "proven_best": p.info["proven"], "solve_seconds": round(p.info["seconds"], 3),
            "stalled_job": _as_dict(p.assign[ro_id]), "changes": changes, "late_orders": late,
            "assignments": {jid: _as_dict(a) for jid, a in p.assign.items()},
        })
    if not options:
        raise StallError(409, "The engine could not find a workable plan.")
    if len(options) == 2 and options[0]["assignments"] == options[1]["assignments"] and options[0]["source_id"] == options[1]["source_id"]:
        options = [dict(options[0], title="Recommended plan")]
    return options


def _no_replan(shop, jobs, prev, now, stall, source, pinned, in_progress):
    """What happens if nobody re-plans and the shop simply waits for the part."""
    if in_progress:
        base = right_shift(shop, jobs, prev, now, stall, source, pinned)
    else:
        waiting = [replace(j, release=max(j.release, now + source.eta)) if j.id == stall.job else j for j in jobs]
        base = right_shift(shop, waiting, prev, now, pinned=pinned)
    bm = metrics(jobs, base)
    return {"source_id": source.id, "source_name": source.name, "arrives_min": now + source.eta,
            "missed_promises": bm["late"], "late_minutes": bm["tard"], "bay_blocked_min": base.hold}


def _store(conn, now, payload):
    conn.execute("UPDATE proposals SET status = 'replaced' WHERE status = 'open'")
    cur = conn.execute("INSERT INTO proposals (created_min, plan_version, ro_id, part_id, status, payload) VALUES (?, ?, ?, ?, 'open', ?)",
                       (now, db.get_meta(conn, "plan_version", 1), payload["ro_id"], payload["part_id"], json.dumps(payload)))
    conn.commit()
    return get(conn, cur.lastrowid)


def propose(conn, ro_id, part_id, force_source=None):
    """A part is missing. Work out the sources and plan options, store them, and return them."""
    now = db.get_meta(conn, "now_min", 0)
    order = conn.execute("SELECT * FROM repair_orders WHERE id = ?", (ro_id,)).fetchone()
    if order is None:
        raise StallError(404, f"There is no repair order {ro_id}.")
    need = conn.execute("SELECT qty FROM ro_parts WHERE ro_id = ? AND part_id = ?", (ro_id, part_id)).fetchone()
    part = conn.execute("SELECT * FROM parts WHERE id = ?", (part_id,)).fetchone()
    if need is None or part is None:
        raise StallError(409, f"{ro_id} does not use part {part_id}.")
    if conn.execute("SELECT 1 FROM sourced WHERE ro_id = ? AND part_id = ?", (ro_id, part_id)).fetchone():
        raise StallError(409, f"{part['name']} is already on its way for {ro_id}.")
    shop, jobs, plan, pinned, blocks = repo.load_engine(conn)
    if ro_id in pinned:
        raise StallError(409, f"{ro_id} is already waiting for a part.")
    current = plan.assign[ro_id]
    if current.end <= now:
        raise StallError(409, f"{ro_id} is already finished.")
    in_progress = current.start <= now

    cands = sourcing.candidates(conn, part_id, need["qty"])
    usable = [c for c in cands if c["available"]]
    if force_source and force_source not in {c["id"] for c in usable}:
        raise StallError(422, "That source does not have the part.")
    sources = tuple(Source(c["id"], c["name"], c["eta_min"], c["cost"], c["risk"] or 0.0, c["safe"]) for c in usable)
    stall = Stall(ro_id, part["name"], sources)
    options = _solve(conn, shop, jobs, plan, plan, now, stall, pinned, blocks, force_source)
    cheapest = min((s for s in sources if s.safe), key=lambda s: (s.cost, s.eta))
    return _store(conn, now, {
        "kind": "missing_part", "ro_id": ro_id, "vehicle": order["vehicle"], "description": order["description"], "promise_min": order["promise_min"],
        "part_id": part_id, "part_name": part["name"], "qty": need["qty"], "now_min": now, "in_progress": in_progress,
        "forced_source": force_source, "current": _as_dict(current), "sources": cands, "options": options,
        "no_replan": _no_replan(shop, jobs, plan, now, stall, cheapest, pinned, in_progress),
    })


def check_late(conn, ro_id, part_id, arrives_min):
    """A part that is already on its way will arrive at a different time. Does the plan still hold?

    If the job was not due to (re)start before the new arrival, nothing has to change. If it was,
    the engine re-plans around the new arrival time. Nothing is saved here except the proposal."""
    now = db.get_meta(conn, "now_min", 0)
    src = conn.execute("SELECT * FROM sourced WHERE ro_id = ? AND part_id = ?", (ro_id, part_id)).fetchone()
    if src is None:
        raise StallError(409, f"No part is on its way for {ro_id}.")
    if arrives_min < now:
        raise StallError(422, "The new arrival time cannot be in the past.")
    order = conn.execute("SELECT * FROM repair_orders WHERE id = ?", (ro_id,)).fetchone()
    part = conn.execute("SELECT * FROM parts WHERE id = ?", (part_id,)).fetchone()
    shop, jobs, plan, pinned, blocks = repo.load_engine(conn)
    current = plan.assign[ro_id]
    if current.end <= now:
        raise StallError(409, f"{ro_id} is already finished.")
    if current.start <= now and ro_id not in pinned:
        raise StallError(409, f"{ro_id} is already being worked on with its part.")
    if arrives_min <= current.start:
        # Any plan drafted for a later arrival time is no longer relevant.
        conn.execute("UPDATE proposals SET status = 'replaced' WHERE status = 'open' AND ro_id = ? AND part_id = ?", (ro_id, part_id))
        conn.commit()
        return {"holds": True, "starts_min": current.start, "spare_min": current.start - arrives_min, "arrives_min": arrives_min}

    waiting = ro_id in pinned  # the car is dismantled and its bay is blocked
    source = Source(src["source_id"], src["source_name"], arrives_min - now, 0, 0.0, True)
    stall = Stall(ro_id, part["name"], (source,))
    prev, pins, blks = plan, pinned, blocks
    if waiting:
        # Re-time the waiting job: treat the rest of its work as in progress from now, in the same bay.
        done = conn.execute("SELECT * FROM segments WHERE ro_id = ? AND kind = 'done'", (ro_id,)).fetchone()
        rest = current.end - current.start
        virtual = Assign(min(done["start_min"], now), now + rest, done["tech_id"], current.bay)
        prev = Plan(assign={**plan.assign, ro_id: virtual})
        pins = pinned - {ro_id}
        blks = tuple((r["bay_id"], r["start_min"], r["end_min"]) for r in conn.execute("SELECT * FROM segments WHERE kind = 'hold' AND ro_id != ?", (ro_id,)))
    options = _solve(conn, shop, jobs, plan, prev, now, stall, pins, blks)
    proposal = _store(conn, now, {
        "kind": "late_part", "ro_id": ro_id, "vehicle": order["vehicle"], "description": order["description"], "promise_min": order["promise_min"],
        "part_id": part_id, "part_name": part["name"], "qty": 0, "now_min": now, "in_progress": waiting,
        "forced_source": None, "current": _as_dict(current), "old_arrives_min": src["arrives_min"], "new_arrives_min": arrives_min,
        "sources": [{"id": src["source_id"], "name": src["source_name"], "kind": "on_its_way", "eta_min": arrives_min - now, "cost": src["cost"],
                     "on_hand": None, "available": True, "risk": None, "risk_basis": None, "safe": True}],
        "options": options, "no_replan": _no_replan(shop, jobs, prev, now, stall, source, pins, waiting),
    })
    return {"holds": False, "proposal": proposal}


def confirm_late(conn, ro_id, part_id, arrives_min):
    """Record a new arrival time that the plan can absorb."""
    result = check_late(conn, ro_id, part_id, arrives_min)
    if not result["holds"]:
        raise StallError(409, "The plan does not hold with that arrival time. Approve one of the new plans instead.")
    now = db.get_meta(conn, "now_min", 0)
    old = conn.execute("SELECT arrives_min FROM sourced WHERE ro_id = ? AND part_id = ?", (ro_id, part_id)).fetchone()["arrives_min"]
    conn.execute("UPDATE sourced SET arrives_min = ? WHERE ro_id = ? AND part_id = ?", (arrives_min, ro_id, part_id))
    part = conn.execute("SELECT name FROM parts WHERE id = ?", (part_id,)).fetchone()["name"]
    conn.execute("INSERT INTO audit_log (at_min, kind, detail) VALUES (?, 'part_late_plan_holds', ?)",
                 (now, json.dumps({"ro_id": ro_id, "part": part, "old_arrives_min": old, "arrives_min": arrives_min, "starts_min": result["starts_min"], "spare_min": result["spare_min"]})))
    conn.commit()
    return result


def get(conn, proposal_id):
    row = conn.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
    if row is None:
        raise StallError(404, "There is no such proposal.")
    return {"id": row["id"], "status": row["status"], "plan_version": row["plan_version"], **json.loads(row["payload"])}


def _customer_message(vehicle, ro_id, promise_min, end_min):
    """Fixed wording for now. An LLM will draft this later; it will never change the plan."""
    return (f"Update on your {vehicle} ({ro_id}): a part for the repair had to be brought in from another location. "
            f"It will be ready at {repo.clock(end_min)}, not {repo.clock(promise_min)} as promised. We are sorry for the delay.")


def approve(conn, proposal_id, option_key):
    """Make one option the live plan, and record what was decided."""
    p = get(conn, proposal_id)
    if p["status"] != "open":
        raise StallError(409, "This proposal is no longer open.")
    if p["plan_version"] != db.get_meta(conn, "plan_version", 1):
        raise StallError(409, "The plan changed after this proposal was made. Report the stall again.")
    opt = next((o for o in p["options"] if o["key"] == option_key), None)
    if opt is None:
        raise StallError(422, "That plan option does not exist.")
    now, ro_id, late = p["now_min"], p["ro_id"], p["kind"] == "late_part"
    for jid, a in opt["assignments"].items():
        conn.execute("UPDATE assignments SET start_min = ?, end_min = ?, tech_id = ?, bay_id = ? WHERE ro_id = ?",
                     (a["start_min"], a["end_min"], a["technician"], a["bay"], jid))
    if late and p["in_progress"]:
        conn.execute("UPDATE segments SET end_min = ? WHERE ro_id = ? AND kind = 'hold'", (opt["stalled_job"]["start_min"], ro_id))
    elif p["in_progress"]:
        cur = p["current"]
        conn.execute("INSERT INTO segments (ro_id, kind, start_min, end_min, tech_id, bay_id) VALUES (?, 'done', ?, ?, ?, ?)",
                     (ro_id, cur["start_min"], now, cur["technician"], cur["bay"]))
        conn.execute("INSERT INTO segments (ro_id, kind, start_min, end_min, tech_id, bay_id) VALUES (?, 'hold', ?, ?, NULL, ?)",
                     (ro_id, now, opt["stalled_job"]["start_min"], cur["bay"]))
    else:
        conn.execute("UPDATE repair_orders SET release_min = MAX(release_min, ?) WHERE id = ?", (opt["arrives_min"], ro_id))
    if late:
        conn.execute("UPDATE sourced SET arrives_min = ? WHERE ro_id = ? AND part_id = ?", (opt["arrives_min"], ro_id, p["part_id"]))
    else:
        conn.execute("INSERT INTO sourced VALUES (?, ?, ?, ?, ?, ?)", (ro_id, p["part_id"], opt["source_id"], opt["source_name"], opt["arrives_min"], opt["cost"]))
        conn.execute("UPDATE stock SET on_hand = on_hand - ? WHERE store_id = ? AND part_id = ?", (p["qty"], opt["source_id"], p["part_id"]))
    messages = [{"ro_id": o["ro_id"], "text": _customer_message(o["vehicle"], o["ro_id"], o["promise_min"], o["end_min"])}
                for o in opt["late_orders"] if not o["late_before"] or o["ro_id"] == ro_id]
    detail = {"ro_id": ro_id, "part": p["part_name"], "source": opt["source_name"], "arrives_min": opt["arrives_min"], "cost": 0 if late else opt["cost"],
              "option": opt["title"], "missed_promises": opt["missed_promises"], "jobs_moved": [c["ro_id"] for c in opt["changes"]],
              "bay_blocked_min": opt["bay_blocked_min"], "proven_best": opt["proven_best"],
              "customer_messages": messages, "messages_written_by": "fixed template (LLM not connected)"}
    if late:
        detail["old_arrives_min"] = p["old_arrives_min"]
    conn.execute("INSERT INTO audit_log (at_min, kind, detail) VALUES (?, ?, ?)", (now, "part_late_replanned" if late else "stall_resolved", json.dumps(detail)))
    conn.execute("UPDATE proposals SET status = 'approved' WHERE id = ?", (proposal_id,))
    conn.commit()
    db.set_meta(conn, "plan_version", p["plan_version"] + 1)
    return detail


def dismiss(conn, proposal_id):
    get(conn, proposal_id)
    conn.execute("UPDATE proposals SET status = 'dismissed' WHERE id = ? AND status = 'open'", (proposal_id,))
    conn.commit()

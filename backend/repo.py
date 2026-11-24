"""Read the database into the engine's own types, and into plain dicts for the API."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from shopcore import Assign, Bay, Job, Plan, Shop, Tech  # noqa: E402

from . import db  # noqa: E402


def clock(minutes):
    return f"{8 + minutes // 60:02d}:{minutes % 60:02d}"


def load_engine(conn):
    """Shop, jobs and the current plan, as the solver expects them, plus what must stay put:
    the remaining work of jobs already stalled (pinned) and the bays they are blocking."""
    techs = tuple(Tech(r["id"], frozenset(json.loads(r["skills"]))) for r in conn.execute("SELECT * FROM technicians ORDER BY rowid"))
    bays = tuple(Bay(r["id"], r["kind"]) for r in conn.execute("SELECT * FROM bays ORDER BY rowid"))
    jobs = [Job(r["id"], r["description"], r["minutes"], r["skill"], tuple(json.loads(r["bay_kinds"])), due=r["promise_min"], release=r["release_min"])
            for r in conn.execute("SELECT * FROM repair_orders ORDER BY id")]
    assign = {r["ro_id"]: Assign(r["start_min"], r["end_min"], r["tech_id"], r["bay_id"]) for r in conn.execute("SELECT * FROM assignments")}
    pinned = frozenset(r["ro_id"] for r in conn.execute("SELECT DISTINCT ro_id FROM segments"))
    blocks = tuple((r["bay_id"], r["start_min"], r["end_min"]) for r in conn.execute("SELECT * FROM segments WHERE kind = 'hold'"))
    return Shop(techs, bays), jobs, Plan(assign=assign), pinned, blocks


def status_of(start, end, now):
    if end <= now:
        return "done"
    if start < now:  # a job that starts this minute has not been taken apart yet
        return "in_progress"
    return "scheduled"


def peg(conn, now):
    """Hand out the home store's stock to the jobs that were open when it was counted, in the
    order they start. Jobs that have finished since still used their parts, so they count against
    the shelf, but only jobs still open now are flagged.

    Returns {(ro_id, part_id): reason} for every need that cannot be met: 'out_of_stock' when the
    shelf is empty, 'claimed_by_earlier_jobs' when earlier jobs today will use what is there.
    Parts already ordered for a job are skipped."""
    shelf = {r["part_id"]: r["on_hand"] for r in conn.execute("SELECT part_id, on_hand FROM stock WHERE store_id = (SELECT id FROM stores WHERE is_home = 1)")}
    start_stock = dict(shelf)
    ordered = {(r["ro_id"], r["part_id"]) for r in conn.execute("SELECT ro_id, part_id FROM sourced")}
    short = {}
    rows = conn.execute("""SELECT p.ro_id, p.part_id, p.qty FROM ro_parts p JOIN assignments a ON a.ro_id = p.ro_id
                           WHERE a.end_min > ? ORDER BY a.start_min, p.ro_id, p.part_id""", (db.get_meta(conn, "stock_counted_min", 0),))
    finished = {r["ro_id"] for r in conn.execute("SELECT ro_id FROM assignments WHERE end_min <= ?", (now,))}
    for r in rows:
        key = (r["ro_id"], r["part_id"])
        if key in ordered:
            continue
        if shelf.get(r["part_id"], 0) >= r["qty"]:
            shelf[r["part_id"]] -= r["qty"]
        elif r["ro_id"] not in finished:
            short[key] = "out_of_stock" if start_stock.get(r["part_id"], 0) < r["qty"] else "claimed_by_earlier_jobs"
    return short


def day(conn):
    """Everything the schedule board needs, in one response."""
    now = db.get_meta(conn, "now_min", 0)
    home = conn.execute("SELECT * FROM stores WHERE is_home = 1").fetchone()
    stock = {(r["store_id"], r["part_id"]): r["on_hand"] for r in conn.execute("SELECT * FROM stock")}
    part_name = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM parts")}
    sourced = {(r["ro_id"], r["part_id"]): r for r in conn.execute("SELECT * FROM sourced")}
    segments = [{"ro_id": r["ro_id"], "kind": r["kind"], "start_min": r["start_min"], "end_min": r["end_min"], "technician": r["tech_id"], "bay": r["bay_id"]}
                for r in conn.execute("SELECT * FROM segments ORDER BY id")]
    holds = {s["ro_id"]: s for s in segments if s["kind"] == "hold"}
    shortfalls = peg(conn, now)
    needs = {}
    for r in conn.execute("SELECT * FROM ro_parts ORDER BY part_id"):
        src = sourced.get((r["ro_id"], r["part_id"]))
        needs.setdefault(r["ro_id"], []).append({
            "part_id": r["part_id"], "name": part_name[r["part_id"]], "qty": r["qty"],
            "on_hand_home": stock.get((home["id"], r["part_id"]), 0),
            "sourced_from": src["source_name"] if src else None, "arrives_min": src["arrives_min"] if src else None,
            "shortfall": shortfalls.get((r["ro_id"], r["part_id"]))})
    assign = {r["ro_id"]: r for r in conn.execute("SELECT * FROM assignments")}
    orders = []
    for r in conn.execute("SELECT * FROM repair_orders ORDER BY id"):
        a = assign.get(r["id"])
        orders.append({
            "id": r["id"], "vehicle": r["vehicle"], "description": r["description"], "minutes": r["minutes"], "skill": r["skill"],
            "release_min": r["release_min"], "promise_min": r["promise_min"], "parts": needs.get(r["id"], []),
            "start_min": a["start_min"] if a else None, "end_min": a["end_min"] if a else None,
            "technician": a["tech_id"] if a else None, "bay": a["bay_id"] if a else None,
            "status": ("waiting_for_part" if r["id"] in holds and now < holds[r["id"]]["end_min"]
                       else status_of(a["start_min"], a["end_min"], now)) if a else "unplanned",
            "late": bool(a and a["end_min"] > r["promise_min"]),
            "short_of_parts": any(p["shortfall"] for p in needs.get(r["id"], [])),
        })
    planned = [o for o in orders if o["end_min"] is not None]
    return {
        "store": {"id": home["id"], "name": home["name"]},
        "sister_stores": [{"id": r["id"], "name": r["name"], "shuttle_minutes": r["shuttle_minutes"]} for r in conn.execute("SELECT * FROM stores WHERE is_home = 0 ORDER BY shuttle_minutes")],
        "now_min": now, "day_start_clock": "08:00", "horizon_min": 600,
        "plan_version": db.get_meta(conn, "plan_version", 1),
        "technicians": [{"id": r["id"], "name": r["name"], "skills": json.loads(r["skills"])} for r in conn.execute("SELECT * FROM technicians ORDER BY rowid")],
        "bays": [{"id": r["id"], "name": r["name"], "kind": r["kind"]} for r in conn.execute("SELECT * FROM bays ORDER BY rowid")],
        "orders": orders,
        "segments": segments,
        "open_proposal_id": (conn.execute("SELECT id FROM proposals WHERE status = 'open' ORDER BY id DESC LIMIT 1").fetchone() or [None])[0],
        "summary": {
            "orders": len(orders),
            "done": sum(o["status"] == "done" for o in orders),
            "in_progress": sum(o["status"] == "in_progress" for o in orders),
            "waiting_for_part": sum(o["status"] == "waiting_for_part" for o in orders),
            "scheduled": sum(o["status"] == "scheduled" for o in orders),
            "promises_at_risk": sum(o["late"] for o in planned),
            "last_finish_min": max((o["end_min"] for o in planned), default=0),
        },
    }

"""The parts check: find jobs that will run out of a part before anyone takes the car apart.

In a real dealership this would run every night for the next day. In the demo it runs on the
jobs still open today. For each shortfall it works out whether a safe source can deliver before
the job is due to start. If so, the part can be ordered without touching the schedule; if not,
the job needs a re-plan, which is the stall flow.
"""
import json

from . import db, repo, sourcing


def _best_in_time(conn, part_id, qty, now, start_min):
    """Cheapest safe source that arrives before the job starts, or None."""
    ok = [c for c in sourcing.candidates(conn, part_id, qty) if c["available"] and c["safe"] and now + c["eta_min"] <= start_min]
    return min(ok, key=lambda c: (c["cost"], c["eta_min"])) if ok else None


def run(conn):
    now = db.get_meta(conn, "now_min", 0)
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM parts")}
    qty = {(r["ro_id"], r["part_id"]): r["qty"] for r in conn.execute("SELECT * FROM ro_parts")}
    orders = {r["id"]: r for r in conn.execute("""SELECT o.id, o.vehicle, o.description, o.promise_min, a.start_min, a.end_min, a.bay_id
                                                   FROM repair_orders o JOIN assignments a ON a.ro_id = o.id""")}
    waiting = {r["ro_id"] for r in conn.execute("SELECT DISTINCT ro_id FROM segments")}
    open_jobs = conn.execute("SELECT COUNT(*) FROM assignments WHERE end_min > ?", (now,)).fetchone()[0]
    flagged = []
    for (ro_id, part_id), reason in repo.peg(conn, now).items():
        o = orders[ro_id]
        started = o["start_min"] <= now or ro_id in waiting
        best = None if started else _best_in_time(conn, part_id, qty[(ro_id, part_id)], now, o["start_min"])
        flagged.append({
            "ro_id": ro_id, "vehicle": o["vehicle"], "description": o["description"], "start_min": o["start_min"], "promise_min": o["promise_min"],
            "part_id": part_id, "part_name": names[part_id], "qty": qty[(ro_id, part_id)], "reason": reason, "already_started": started,
            "fix": None if best is None else {"source_id": best["id"], "source_name": best["name"], "arrives_min": now + best["eta_min"], "cost": best["cost"]},
        })
    flagged.sort(key=lambda f: (f["start_min"], f["ro_id"], f["part_id"]))
    quiet = [f for f in flagged if f["fix"]]
    return {"checked_at_min": now, "jobs_checked": open_jobs, "flagged": flagged,
            "fixable_without_replan": len(quiet), "need_a_decision": len(flagged) - len(quiet), "fix_cost": sum(f["fix"]["cost"] for f in quiet)}


def order_fixes(conn):
    """Order every part that a safe source can deliver before its job starts. The schedule is not touched.
    Each order is re-checked against live stock, because one order can use up what another relied on."""
    now = db.get_meta(conn, "now_min", 0)
    placed = []
    for f in run(conn)["flagged"]:
        if not f["fix"]:
            continue
        best = _best_in_time(conn, f["part_id"], f["qty"], now, f["start_min"])
        if best is None:
            continue
        conn.execute("INSERT INTO sourced VALUES (?, ?, ?, ?, ?, ?)", (f["ro_id"], f["part_id"], best["id"], best["name"], now + best["eta_min"], best["cost"]))
        conn.execute("UPDATE stock SET on_hand = on_hand - ? WHERE store_id = ? AND part_id = ?", (f["qty"], best["id"], f["part_id"]))
        conn.execute("UPDATE repair_orders SET release_min = MAX(release_min, ?) WHERE id = ?", (now + best["eta_min"], f["ro_id"]))
        placed.append({"ro_id": f["ro_id"], "part": f["part_name"], "source": best["name"], "arrives_min": now + best["eta_min"],
                       "job_starts_min": f["start_min"], "cost": best["cost"]})
    if placed:
        conn.execute("INSERT INTO audit_log (at_min, kind, detail) VALUES (?, 'parts_ordered_ahead', ?)",
                     (now, json.dumps({"orders": placed, "total_cost": sum(p["cost"] for p in placed)})))
    conn.commit()
    return placed

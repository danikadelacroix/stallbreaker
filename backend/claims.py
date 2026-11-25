"""A part that has been ordered is only a claim by its source until it is in the building (spec 113).

A request is 'requested' when placed, 'confirmed' when a person records that the source said yes,
and 'received' when the part is here. For each request this module works out, from the plan as it
stands, when the part is needed, which other source could step in, and the last moment to switch
to it without changing the plan. Nothing here contacts a source or changes the plan.
"""
from . import sourcing


def place(conn, ro_id, part_id, qty, source_id, source_name, arrives_min, cost, now, moved_from=None):
    """Record a new request and take the part off the lending store's count."""
    conn.execute("""INSERT INTO sourced (ro_id, part_id, source_id, source_name, arrives_min, cost, state, requested_min, moved_from)
                    VALUES (?, ?, ?, ?, ?, ?, 'requested', ?, ?)""", (ro_id, part_id, source_id, source_name, arrives_min, cost, now, moved_from))
    conn.execute("UPDATE stock SET on_hand = on_hand - ? WHERE store_id = ? AND part_id = ?", (qty, source_id, part_id))


def cancel(conn, ro_id, part_id, qty, give_back=True):
    """Drop a request. A sister store gets the part back on its count, unless it said it cannot supply it."""
    row = conn.execute("SELECT source_id FROM sourced WHERE ro_id = ? AND part_id = ?", (ro_id, part_id)).fetchone()
    if row and give_back:
        conn.execute("UPDATE stock SET on_hand = on_hand + ? WHERE store_id = ? AND part_id = ?", (qty, row["source_id"], part_id))
    conn.execute("DELETE FROM sourced WHERE ro_id = ? AND part_id = ?", (ro_id, part_id))


def way_back(conn, part_id, qty, source_id, needed_by_min, placed_min, moved_from=None):
    """The backup for a request: the fastest other safe source that has the part (never the one the request was just moved away from), and the last moment
    it could be ordered and still arrive when the job is due to start. That moment is None if it had
    already passed when the request was placed: there was never a way back that leaves the plan alone."""
    others = [c for c in sourcing.candidates(conn, part_id, qty) if c["available"] and c["safe"] and c["id"] not in (source_id, moved_from)]
    if not others:
        return {"needed_by_min": needed_by_min, "switch_by_min": None, "backup_name": None, "backup_eta_min": None}
    backup = min(others, key=lambda c: (c["eta_min"], c["cost"]))
    switch_by = needed_by_min - backup["eta_min"]
    return {"needed_by_min": needed_by_min, "switch_by_min": switch_by if switch_by > placed_min else None,
            "backup_name": backup["name"], "backup_eta_min": backup["eta_min"]}


def of_day(conn, now, orders):
    """Every request of the day, keyed by (repair order, part), with whether someone should chase it."""
    by_id = {o["id"]: o for o in orders}
    qty = {(r["ro_id"], r["part_id"]): r["qty"] for r in conn.execute("SELECT * FROM ro_parts")}
    out = {}
    for r in conn.execute("SELECT * FROM sourced"):
        key, job = (r["ro_id"], r["part_id"]), by_id[r["ro_id"]]
        back = way_back(conn, r["part_id"], qty[key], r["source_id"], job["start_min"], r["requested_min"], r["moved_from"])
        chase = None
        if r["state"] != "received" and job["status"] != "done":
            ask_by = min(back["switch_by_min"] or r["arrives_min"], r["arrives_min"])
            if r["state"] == "requested" and now >= ask_by:
                chase = "no_answer"
            elif now >= r["arrives_min"]:
                chase = "not_here"
        out[key] = {"state": r["state"], "source_id": r["source_id"], "source_name": r["source_name"], "arrives_min": r["arrives_min"], **back, "chase": chase}
    return out

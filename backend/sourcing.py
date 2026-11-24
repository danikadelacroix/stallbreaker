"""Find every place a missing part could come from, with arrival time, cost and shortage risk."""
from . import risk

TRANSFER_FEE = 15  # shuttle cost for a part moved between sister stores


def candidates(conn, part_id, qty):
    """One entry per sister store and supplier. Stores without enough stock are listed as unavailable."""
    part = conn.execute("SELECT * FROM parts WHERE id = ?", (part_id,)).fetchone()
    out = []
    for store in conn.execute("SELECT * FROM stores WHERE is_home = 0 ORDER BY shuttle_minutes"):
        row = conn.execute("SELECT on_hand FROM stock WHERE store_id = ? AND part_id = ?", (store["id"], part_id)).fetchone()
        on_hand = row["on_hand"] if row else 0
        entry = {"id": store["id"], "name": store["name"], "kind": "sister_store", "eta_min": store["shuttle_minutes"], "cost": TRANSFER_FEE,
                 "on_hand": on_hand, "available": on_hand >= qty, "risk": None, "risk_basis": None, "safe": True}
        if entry["available"]:
            left = on_hand - qty
            r, over, total = risk.shortage_risk(part["series_id"], left)
            if r is None:
                entry.update(safe=False, risk_basis="no demand history for this part, so lending cannot be judged")
            else:
                entry.update(risk=round(r, 3), safe=r <= risk.RISK_LIMIT,
                             risk_basis=f"demand was above {left} in {over} of {total} past months")
        out.append(entry)
    for sup in conn.execute("SELECT * FROM suppliers ORDER BY lead_minutes"):
        out.append({"id": sup["id"], "name": sup["name"], "kind": sup["kind"], "eta_min": sup["lead_minutes"], "cost": sup["surcharge"],
                    "on_hand": None, "available": True, "risk": 0.0, "risk_basis": "an outside supplier, so no store is left short", "safe": True})
    return out

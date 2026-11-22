"""Build the demo dealer group: one home store with a full day of repair orders, two sister
stores, a vendor and an OEM depot. Everything here is invented and seeded, so the same seed
always gives the same day. Part demand histories point at real Monash Car Parts series."""
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from shopcore import Bay, Job, Shop, Tech, dispatch_edd, initial_plan, metrics, validate  # noqa: E402

from . import db  # noqa: E402

DEFAULT_SEED = 2026
START_CLOCK = 150  # 10:30, minutes after 08:00

TECH_NAMES = ["Meera", "Kavya", "Riya", "Ananya", "Diya", "Isha", "Tara", "Nisha", "Pooja", "Sana"]
SKILLSETS = [
    ["engine", "brakes", "general"], ["brakes", "general", "electrical"], ["general", "electrical", "alignment"],
    ["engine", "general", "alignment"], ["brakes", "electrical", "general"],
]
PARTS = [  # id, name, unit cost
    ("OIL-FLT", "Oil filter", 9), ("OIL-5W30", "Engine oil 5W-30, 5 qt", 32), ("CAB-FLT", "Cabin air filter", 18),
    ("AC-RFG", "Refrigerant charge", 45), ("BAT-H6", "Battery, group H6", 165), ("BRK-PAD-F", "Front brake pad set", 68),
    ("BRK-ROT-F", "Front rotor pair", 140), ("BRK-FLD", "Brake fluid DOT 4", 14), ("SUS-ARM-L", "Lower control arm", 120),
    ("SUS-BSH", "Bushing kit", 35), ("TMG-KIT", "Timing belt kit", 190), ("TMG-TNS", "Belt tensioner", 75),
    ("WTR-PMP", "Water pump", 130), ("WTR-GSK", "Water pump gasket kit", 22), ("CLT-5050", "Coolant 50/50, 1 gal", 16),
]
L, F = ["lift"], ["flat"]
JOB_TYPES = [  # code, description, minutes, skill, bay kinds, parts kit, relative frequency
    ("OIL", "Oil service", 45, "general", L + F, {"OIL-FLT": 1, "OIL-5W30": 1}, 6),
    ("DIAG", "Diagnostic scan", 40, "electrical", L + F, {}, 3),
    ("ALIGN", "Wheel alignment", 60, "alignment", F, {}, 3),
    ("BATT", "Battery replacement", 50, "electrical", L + F, {"BAT-H6": 1}, 2),
    ("AC", "AC service", 80, "general", L + F, {"CAB-FLT": 1, "AC-RFG": 1}, 2),
    ("PADS", "Front brake pads", 90, "brakes", L, {"BRK-PAD-F": 1}, 4),
    ("SUSP", "Lower control arm", 110, "general", L, {"SUS-ARM-L": 1, "SUS-BSH": 1}, 2),
    ("ROTOR", "Rotors and brake fluid", 120, "brakes", L, {"BRK-ROT-F": 1, "BRK-PAD-F": 1, "BRK-FLD": 1}, 2),
    ("TBELT", "Timing belt", 150, "engine", L, {"TMG-KIT": 1, "TMG-TNS": 1}, 2),
    ("WPUMP", "Water pump replacement", 180, "engine", L, {"WTR-PMP": 1, "WTR-GSK": 1, "CLT-5050": 1}, 2),
]
VEHICLES = ["Toyota Camry", "Honda Civic", "Ford F-150", "Chevrolet Silverado", "Toyota RAV4", "Honda CR-V", "Nissan Altima",
            "Hyundai Tucson", "Ford Explorer", "Toyota Corolla", "Honda Accord", "Jeep Wrangler", "Subaru Outback", "Kia Sorento"]


def _series_ids(n):
    """Pick n real Monash Car Parts series with steady demand, to drive shortage risk later."""
    path = os.path.join(ROOT, "data", "car_parts_dataset_without_missing_values.tsf")
    totals, in_data = [], False
    for line in open(path, encoding="latin-1"):
        line = line.strip()
        if line.lower() == "@data":
            in_data = True
            continue
        if in_data and line:
            name, _start, vals = line.split(":")
            v = [float(x) for x in vals.split(",")]
            totals.append((sum(1 for x in v if x > 0), sum(v), name))
    totals.sort(reverse=True)
    return [t[2] for t in totals[:n]]


SHORT_BY = {"WTR-GSK": None, "TMG-TNS": 2, "BRK-PAD-F": 2}  # None = none on the shelf at all


def _set_home_stock(conn, plan):
    """Make the home store's shelf match the day: enough of every part for the jobs still open at
    the demo's start time, except three parts that are deliberately short so there is something to find."""
    open_need = {}
    for r in conn.execute("SELECT ro_id, part_id, qty FROM ro_parts"):
        if plan.assign[r["ro_id"]].end > START_CLOCK:
            open_need[r["part_id"]] = open_need.get(r["part_id"], 0) + r["qty"]
    for r in conn.execute("SELECT part_id, on_hand FROM stock WHERE store_id = 'home'").fetchall():
        need = open_need.get(r["part_id"], 0)
        if r["part_id"] in SHORT_BY:
            short = SHORT_BY[r["part_id"]]
            on_hand = 0 if short is None else max(0, need - short)
        else:
            on_hand = max(r["on_hand"], need)
        conn.execute("UPDATE stock SET on_hand = ? WHERE store_id = 'home' AND part_id = ?", (on_hand, r["part_id"]))


def build(conn, seed=DEFAULT_SEED, n_orders=40):
    rng = random.Random(seed)
    db.wipe(conn)
    ex = conn.execute
    ex("INSERT INTO stores VALUES ('home', 'Main Street', 1, 0)")
    ex("INSERT INTO stores VALUES ('north', 'Sister store North', 0, 40)")
    ex("INSERT INTO stores VALUES ('east', 'Sister store East', 0, 110)")
    ex("INSERT INTO suppliers VALUES ('vendor', 'Local vendor', 'vendor', 60, 85)")
    ex("INSERT INTO suppliers VALUES ('oem', 'OEM depot', 'oem', 240, 0)")

    techs = [Tech(TECH_NAMES[i], frozenset(SKILLSETS[i % len(SKILLSETS)])) for i in range(10)]
    bays = [Bay(f"Bay {i + 1}", "lift") for i in range(8)] + [Bay(f"Bay {i + 9}", "flat") for i in range(2)]
    for t in techs:
        ex("INSERT INTO technicians VALUES (?, ?, ?)", (t.id, t.id, json.dumps(sorted(t.skills))))
    for b in bays:
        ex("INSERT INTO bays VALUES (?, ?, ?)", (b.id, b.id, b.kind))

    series = _series_ids(len(PARTS))
    for (pid, name, cost), sid in zip(PARTS, series):
        ex("INSERT INTO parts VALUES (?, ?, ?, ?)", (pid, name, cost, sid))
        # Home store is mostly stocked; two parts are deliberately out so the nightly check has something to find.
        home = 0 if pid in ("WTR-GSK", "TMG-TNS") else rng.randint(2, 6)
        north = 1 if pid == "WTR-GSK" else rng.randint(0, 4)
        east = 6 if pid == "WTR-GSK" else rng.randint(1, 6)
        for store, qty in (("home", home), ("north", north), ("east", east)):
            ex("INSERT INTO stock VALUES (?, ?, ?)", (store, pid, qty))
    for code, desc, minutes, skill, kinds, kit, _w in JOB_TYPES:
        ex("INSERT INTO job_types VALUES (?, ?, ?, ?, ?)", (code, desc, minutes, skill, json.dumps(kinds)))
        for pid, qty in kit.items():
            ex("INSERT INTO job_type_parts VALUES (?, ?, ?)", (code, pid, qty))

    jobs = []
    weights = [jt[6] for jt in JOB_TYPES]
    for i in range(n_orders):
        code, desc, minutes, skill, kinds, kit, _w = rng.choices(JOB_TYPES, weights)[0]
        release = 0 if i < n_orders // 3 else rng.randrange(0, 331, 15)
        promise = release + minutes + rng.randrange(60, 241, 15)
        rid = f"RO-{1001 + i}"
        vehicle = f"{rng.randint(2016, 2024)} {rng.choice(VEHICLES)}"
        ex("INSERT INTO repair_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (rid, vehicle, code, desc, minutes, skill, json.dumps(kinds), release, promise))
        for pid, qty in kit.items():
            ex("INSERT INTO ro_parts VALUES (?, ?, ?)", (rid, pid, qty))
        jobs.append(Job(rid, desc, minutes, skill, tuple(kinds), due=promise, release=release))

    shop = Shop(tuple(techs), tuple(bays))
    plan = initial_plan(shop, jobs, time_limit=6.0, deterministic=True)  # same plan on every reset and every machine
    source = "solver"
    if plan is None:
        plan, source = dispatch_edd(shop, jobs, None, 0), "dispatch rule"
    validate(shop, jobs, plan)
    for rid, a in plan.assign.items():
        ex("INSERT INTO assignments VALUES (?, ?, ?, ?, ?)", (rid, a.start, a.end, a.tech, a.bay))
    _set_home_stock(conn, plan)
    conn.commit()
    db.set_meta(conn, "seed", seed)
    db.set_meta(conn, "now_min", START_CLOCK)
    db.set_meta(conn, "plan_version", 1)
    m = metrics(jobs, plan)
    ex("INSERT INTO audit_log (at_min, kind, detail) VALUES (0, 'morning_plan', ?)",
       (json.dumps({"orders": len(jobs), "missed_promises": m["late"], "built_by": source}),))
    conn.commit()
    return {"orders": len(jobs), "missed_promises": m["late"], "built_by": source,
            "last_finish_min": max(a.end for a in plan.assign.values())}


if __name__ == "__main__":
    print(build(db.connect()))

"""Read a technician's note into a structured report: which repair order, which part, what happened.

Reading changes nothing. The result is shown to a person, who confirms it; only then does the
stall flow or the late-part flow run. Two readers exist: plain rules (always available) and a
language model (if set up). Every reading, from either, passes the same checks in code: the
repair order is open today, the part is one that order needs, a late part is really on its way,
and the quoted words appear in the note.
"""
import difflib
import json
import os
import re

from . import db, llm, repo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_FILE = os.path.join(ROOT, "experiments", "out", "intake_eval.json")

# How people write each part. Longer names win over shorter ones; one-word names such as "kit"
# only count for a job that needs that part.
ALIASES = {
    "OIL-FLT": ["oil filter", "filter"],
    "OIL-5W30": ["engine oil", "5w-30", "5w30", "oil"],
    "CAB-FLT": ["cabin air filter", "cabin filter", "filter"],
    "AC-RFG": ["refrigerant", "freon", "r134a", "charge"],
    "BAT-H6": ["battery", "batt", "h6"],
    "BRK-PAD-F": ["brake pads", "front pads", "pad set", "pads"],
    "BRK-ROT-F": ["rotors", "rotor"],
    "BRK-FLD": ["brake fluid", "dot 4", "dot4", "fluid"],
    "SUS-ARM-L": ["lower control arm", "control arm", "lower arm", "arm"],
    "SUS-BSH": ["bushing kit", "bushings", "bushing", "bushes"],
    "TMG-KIT": ["timing belt kit", "t-belt kit", "belt kit", "timing kit", "kit"],
    "TMG-TNS": ["belt tensioner", "tensioner"],
    "WTR-PMP": ["water pump", "pump", "wp"],
    "WTR-GSK": ["gasket kit", "gasket set", "gskt kit", "gasket", "gskt"],
    "CLT-5050": ["coolant", "antifreeze", "50/50"],
}
_SOMETHING_WRONG = re.compile(r"\b(no|none|not|missing|need|needs|out of|wrong|short|empty|dead|bent|broken|cracked|isn'?t|without|is for the|delayed|late)\b")
_IT_IS_FINE = re.compile(r"^\W*(?:is|are|was|were)?\s*(?:ok|okay|fine|good|here|in stock|arrived|off)\b")
_RUNNING_LATE = re.compile(r"\b(late|delayed|won'?t be here|not here (?:till|until)|now coming|coming at|eta|pushed|till|until)\b")
_CLOCK = re.compile(r"\b(\d{1,2})[:.](\d{2})\s*(am|pm)?|\b(\d{1,2})\s*(am|pm)\b")
_CLAUSE_END = re.compile(r"[,;]|\.(?=\s|$)|\s-\s|:\s|\bbut\b")  # a dot inside "2.0" or "12.30" does not end a clause


def _open_orders(conn):
    return [o for o in repo.day(conn)["orders"] if o["status"] != "done"]


def _order_candidates(note, orders):
    """Narrow the open jobs down by what the note says: a number, or vehicle, year, bay and technician.
    Returns (candidates, reason it is unclear or None)."""
    by_id = {o["id"]: o for o in orders}
    named = re.findall(r"\bro[\s#-]*(\d{3,5})\b", note)
    if named:
        ro = f"RO-{named[0]}"
        return ([by_id[ro]], None) if ro in by_id else ([], f"There is no open repair order {ro} today.")
    bare = [f"RO-{n}" for n in re.findall(r"(?<![\d:.])\b(\d{4})\b(?![:.]\d)", note) if f"RO-{n}" in by_id]
    if bare:
        return [by_id[bare[0]]], None
    words = set(re.findall(r"[a-z0-9]+", note.replace("-", "")))
    cands, used = list(orders), False
    models = {w for o in orders for w in re.findall(r"[a-z0-9]+", o["vehicle"].lower().replace("-", ""))[1:]}
    if words & models:
        cands = [o for o in cands if words & set(re.findall(r"[a-z0-9]+", o["vehicle"].lower().replace("-", ""))[1:])]
        used = True
    years = [y for y in re.findall(r"\b(20[1-3]\d)\b", note)]
    if years:
        cands, used = [o for o in cands if o["vehicle"].startswith(years[0])], True
    bay = re.search(r"\b(?:bay|on|in)\s*#?(\d{1,2})\b", note)
    if bay:
        cands, used = [o for o in cands if o["bay"] == f"Bay {int(bay.group(1))}"], True
    techs = {o["technician"].lower() for o in orders if o["technician"]}
    if words & techs:
        cands, used = [o for o in cands if o["technician"] and o["technician"].lower() in words], True
    if not used or not cands:
        return [], "Could not tell which repair order this is about."
    return cands, None


def _part_mentions(note, part_ids):
    """Every place the note names one of these parts: (start, end, part id). Longer names win where they overlap."""
    found = []
    for pid in part_ids:
        for alias in ALIASES.get(pid, []):
            for m in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", note):
                found.append((m.start(), m.end(), pid))
    for m in re.finditer(r"[a-z]{6,}", note):  # one spelling slip in a long word, e.g. "tensionr"
        for pid in part_ids:
            singles = [a for a in ALIASES.get(pid, []) if " " not in a and len(a) >= 6]
            if m.group() not in singles and difflib.get_close_matches(m.group(), singles, n=1, cutoff=0.85):
                found.append((m.start(), m.end(), pid))
    kept = []
    for f in sorted(found, key=lambda f: f[0] - f[1]):  # longest first
        if all(f[1] <= k[0] or f[0] >= k[1] for k in kept):
            kept.append(f)
    kept.sort()
    # "water pump gasket set", "control arm bushing kit": the first name only describes the second.
    return [f for i, f in enumerate(kept) if not (i + 1 < len(kept) and note[f[1]:kept[i + 1][0]].strip() == "")]


def _clause(note, start, end):
    cuts = [m.end() for m in _CLAUSE_END.finditer(note) if m.end() <= start]
    stops = [m.start() for m in _CLAUSE_END.finditer(note) if m.start() >= end]
    return (cuts[-1] if cuts else 0), (stops[0] if stops else len(note))


def _pick_part(note, mentions):
    """The part the note says is wrong: one with a complaint next to it, never one the note says is fine."""
    best, best_score = None, 0
    for start, end, pid in mentions:
        c0, c1 = _clause(note, start, end)
        if _IT_IS_FINE.match(note[end:c1]):
            continue  # "pump is here", "pads ok", "wp off"
        near = note[max(c0, start - 14):start] + " " + note[end:min(c1, end + 14)]
        score = (end - start) + (200 if _SOMETHING_WRONG.search(near) else 100 if _SOMETHING_WRONG.search(note[c0:c1]) else 0)
        if score > best_score:
            best, best_score = (start, end, pid, c0, c1), score
    return best


def _clock_time(note, now):
    """The first clock time after the words that say something is late, as minutes after 08:00."""
    cue = _RUNNING_LATE.search(note)
    m = _CLOCK.search(note, cue.end() if cue else 0) or _CLOCK.search(note)
    if not m:
        return None
    hour, minute, half = (int(m.group(1)), int(m.group(2)), m.group(3)) if m.group(1) else (int(m.group(4)), 0, m.group(5))
    if half == "pm" and hour < 12 or half is None and hour < 8:  # a shop that opens at 08:00: "2:15" means the afternoon
        hour += 12
    return (hour - 8) * 60 + minute


def _unclear(why):
    return {"kind": "unclear", "ro_id": None, "part_id": None, "arrives_min": None, "quote": None, "why_unclear": why}


def read_with_rules(conn, text):
    """Read a note with plain rules. Works with no key and no internet."""
    note = text.lower()
    now = db.get_meta(conn, "now_min", 0)
    orders = _open_orders(conn)
    cands, why = _order_candidates(note, orders)
    if not cands:
        return _unclear(why)
    kit = {p["part_id"] for o in cands for p in o["parts"]}
    picked = _pick_part(note, _part_mentions(note, sorted(kit)))
    if picked is None:
        which = cands[0]["id"] if len(cands) == 1 else "this job"
        return _unclear(f"Could not tell which part of {which} is the problem.")
    start, end, part_id, c0, c1 = picked
    cands = [o for o in cands if any(p["part_id"] == part_id for p in o["parts"])]
    if len(cands) > 1:
        cands = [o for o in cands if o["status"] == "in_progress"] or cands
    if len(cands) != 1:
        return _unclear("More than one open job matches this note. Add the repair order number.")
    order = cands[0]
    need = next(p for p in order["parts"] if p["part_id"] == part_id)
    reading = {"kind": "missing_part", "ro_id": order["id"], "part_id": part_id, "arrives_min": None,
               "quote": text[c0:c1].strip(" ,;.-:"), "why_unclear": None}
    arrives = _clock_time(note, now) if _RUNNING_LATE.search(note) else None
    if arrives is not None and need["sourced_from"]:
        reading.update(kind="late_part", arrives_min=arrives)
    return check(conn, reading, text)


def check(conn, reading, text):
    """The rules every reading must pass, whoever made it. A reading that fails comes back unclear, with the reason."""
    if not isinstance(reading, dict) or reading.get("kind") not in ("missing_part", "late_part", "unclear"):
        return _unclear("The reading was not in the expected form.")
    if reading["kind"] == "unclear":
        return _unclear(reading.get("why_unclear") or "Could not tell what this note is about.")
    now = db.get_meta(conn, "now_min", 0)
    order = next((o for o in _open_orders(conn) if o["id"] == reading.get("ro_id")), None)
    if order is None:
        return _unclear(f"There is no open repair order {reading.get('ro_id')} today.")
    need = next((p for p in order["parts"] if p["part_id"] == reading.get("part_id")), None)
    if need is None:
        return _unclear(f"{order['id']} does not need that part.")
    quote = reading.get("quote")
    if not quote or quote.lower() not in text.lower():
        return _unclear("The words quoted are not in the note.")
    arrives = reading.get("arrives_min")
    if reading["kind"] == "late_part":
        if not need["sourced_from"]:
            return _unclear(f"No {need['name'].lower()} is on its way for {order['id']}, so it cannot be late.")
        if not isinstance(arrives, int) or arrives <= now or arrives > 900:
            return _unclear("Could not read a new arrival time later than now.")
    elif need["sourced_from"]:
        return _unclear(f"{need['name']} is already on its way for {order['id']}.")
    return {"kind": reading["kind"], "ro_id": order["id"], "part_id": need["part_id"],
            "arrives_min": arrives if reading["kind"] == "late_part" else None, "quote": quote, "why_unclear": None}


SYSTEM = ("You read short notes from car service technicians. Decide whether the note reports a part that is missing or "
          "wrong for a repair order (missing_part), a part already on its way that will arrive at a new time (late_part), "
          "or neither (unclear). Choose the repair order and the part only from the lists given. Copy into 'quote' the exact "
          "words from the note that your reading rests on. If you are not sure, answer unclear. Never guess.")
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["kind", "ro_id", "part_id", "arrives_clock", "quote"],
          "properties": {"kind": {"type": "string", "enum": ["missing_part", "late_part", "unclear"]},
                         "ro_id": {"type": ["string", "null"]}, "part_id": {"type": ["string", "null"]},
                         "arrives_clock": {"type": ["string", "null"], "description": "24-hour HH:MM, only for late_part"},
                         "quote": {"type": ["string", "null"]}}}


def _question(conn, text):
    """What the model is shown: the note with personal details removed, and the lists it must choose from."""
    jobs = [{"ro_id": o["id"], "vehicle": o["vehicle"], "job": o["description"], "bay": o["bay"], "technician": o["technician"],
             "status": o["status"], "parts": [{"part_id": p["part_id"], "name": p["name"], "on_its_way": bool(p["sourced_from"])} for p in o["parts"]]}
            for o in _open_orders(conn)]
    return json.dumps({"note": llm.redact(text), "time_now": repo.clock(db.get_meta(conn, "now_min", 0)), "open_repair_orders": jobs})


def _from_model(conn, answer, text):
    """Turn a model's answer into a checked reading, or say why it was thrown away."""
    if not isinstance(answer, dict):
        return None, "the model gave no usable answer"
    reading = dict(answer)
    clock = reading.pop("arrives_clock", None)
    if isinstance(clock, str) and re.fullmatch(r"\d{1,2}:\d{2}", clock):
        hour, minute = map(int, clock.split(":"))
        reading["arrives_min"] = (hour - 8) * 60 + minute
    reading.setdefault("arrives_min", None)
    if reading.get("kind") == "unclear":
        return None, "the model could not read the note"
    checked = check(conn, reading, text)
    if checked["kind"] == "unclear":
        return None, "the model's answer failed a check: " + checked["why_unclear"]
    return checked, None


def _describe(conn, reading):
    """Add the words a person needs to confirm the reading."""
    order = next((o for o in repo.day(conn)["orders"] if o["id"] == reading["ro_id"]), None)
    part = next((p for p in order["parts"] if p["part_id"] == reading["part_id"]), None) if order else None
    return {**reading, "vehicle": order["vehicle"] if order else None, "description": order["description"] if order else None,
            "part_name": part["name"] if part else None}


def read(conn, text):
    """Read a note with the model if one is set up, otherwise (or if it fails a check) with the rules. Saves nothing."""
    ask, fell_back_because = llm.reader(), None
    if ask is not None:
        reading, fell_back_because = _from_model(conn, ask(SYSTEM, _question(conn, text), SCHEMA), text)
        if reading is not None:
            return {**_describe(conn, reading), "read_by": f"model: {ask.name}", "fell_back_because": None}
    return {**_describe(conn, read_with_rules(conn, text)), "read_by": "rules", "fell_back_because": fell_back_because}


def same_reading(got, expected):
    """Scoring rule for the test set: an unclear note must come out unclear; otherwise order, part and time must all match."""
    if got["kind"] != expected["kind"]:
        return False
    if expected["kind"] == "unclear":
        return True
    return (got["ro_id"], got["part_id"], got["arrives_min"]) == (expected["ro_id"], expected["part_id"], expected["arrives_min"])


def info():
    ask = llm.reader()
    score = json.load(open(EVAL_FILE)) if os.path.exists(EVAL_FILE) else None
    return {"reader": f"model: {ask.name}" if ask else "rules", "sends_notes_out": ask is not None, "eval": score}

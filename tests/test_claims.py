"""Checks on parts that are ordered but not yet here (spec 113). Run:  .venv/bin/python -m pytest -q"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("STALLBREAKER_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

from backend import app as app_module, repo, sourcing  # noqa: E402
from shopcore import validate  # noqa: E402

client = TestClient(app_module.app)
GASKET = {"ro_id": "RO-1013", "part_id": "WTR-GSK"}      # a car on the lift at 11:00 with no gasket kit
TENSIONER = {"ro_id": "RO-1017", "part_id": "TMG-TNS"}   # ordered ahead from Sister store North
PADS_A = {"ro_id": "RO-1035", "part_id": "BRK-PAD-F"}    # ordered ahead from Sister store East
PADS_B = {"ro_id": "RO-1040", "part_id": "BRK-PAD-F"}    # the same


def at_eleven(order_ahead=False):
    client.post("/api/reset")
    day = client.post("/api/clock", json={"now_min": 180}).json()
    return client.post("/api/precheck/order").json()["day"] if order_ahead else day


def clock(minute):
    return client.post("/api/clock", json={"now_min": minute}).json()


def order_of(day, ro_id):
    return next(o for o in day["orders"] if o["id"] == ro_id)


def request_of(day, which):
    return next(p for p in order_of(day, which["ro_id"])["parts"] if p["part_id"] == which["part_id"])["request"]


def the_plan(day):
    return [(o["id"], o["start_min"], o["end_min"], o["bay"], o["technician"]) for o in day["orders"]]


def stall_and_approve(which=GASKET):
    proposal = client.post("/api/stalls", json=which).json()
    option = proposal["options"][0]
    day = client.post(f"/api/proposals/{proposal['id']}/approve", json={"option": option["key"]}).json()["day"]
    return option, day


def replan(which, **more):
    return client.post("/api/late/replan", json={**which, **more})


def approve(proposal, option=None):
    option = option or proposal["options"][0]
    r = client.post(f"/api/proposals/{proposal['id']}/approve", json={"option": option["key"]})
    assert r.status_code == 200, r.text
    return r.json()["day"]


def fastest_other_safe(part_id, not_from):
    usable = [c for c in sourcing.candidates(app_module.conn(), part_id, 1) if c["available"] and c["safe"] and c["id"] not in not_from]
    return min(usable, key=lambda c: c["eta_min"])


def on_hand(store_id, part_id):
    return app_module.conn().execute("SELECT on_hand FROM stock WHERE store_id = ? AND part_id = ?", (store_id, part_id)).fetchone()["on_hand"]


def answer(which, what):
    return client.post("/api/requests/answer", json={**which, "answer": what})


def test_an_ordered_part_is_only_requested_until_a_person_says_otherwise():
    day = at_eleven(order_ahead=True)
    ahead = request_of(day, TENSIONER)
    assert ahead["state"] == "requested" and ahead["source_name"] == "Sister store North"
    assert request_of(day, GASKET) is None, "nothing has been ordered for this part yet"
    option, day = stall_and_approve()
    assert request_of(day, GASKET)["state"] == "requested" and request_of(day, GASKET)["source_id"] == option["source_id"]
    before = the_plan(day)
    day = answer(GASKET, "confirmed").json()["day"]
    assert request_of(day, GASKET)["state"] == "confirmed" and the_plan(day) == before
    log = client.get("/api/log").json()[0]
    assert log["kind"] == "request_answered" and log["detail"]["answer"] == "confirmed" and log["detail"]["ro_id"] == "RO-1013"
    day = answer(GASKET, "received").json()["day"]
    assert request_of(day, GASKET)["state"] == "received" and the_plan(day) == before
    assert answer({"ro_id": "RO-1001", "part_id": "OIL-FLT"}, "confirmed").status_code == 409, "nothing is on its way for this job"
    assert answer(GASKET, "probably").status_code == 422


def test_a_request_says_when_the_part_is_needed_and_the_last_moment_to_switch():
    day = at_eleven(order_ahead=True)
    for which in (TENSIONER, PADS_A, PADS_B):
        req, job = request_of(day, which), order_of(day, which["ro_id"])
        backup = fastest_other_safe(which["part_id"], {req["source_id"]})
        assert req["needed_by_min"] == job["start_min"] >= req["arrives_min"]
        assert (req["backup_name"], req["backup_eta_min"]) == (backup["name"], backup["eta_min"])
        assert req["switch_by_min"] == job["start_min"] - backup["eta_min"]
    tensioner = request_of(day, TENSIONER)
    assert (tensioner["arrives_min"], tensioner["needed_by_min"], tensioner["backup_name"], tensioner["switch_by_min"]) == (220, 255, "Local vendor", 195)


def test_a_plan_says_before_approval_whether_there_is_a_way_back():
    at_eleven()
    proposal = client.post("/api/stalls", json=GASKET).json()
    option = proposal["options"][0]
    assert option["needed_by_min"] == option["stalled_job"]["start_min"]
    backup = fastest_other_safe("WTR-GSK", {option["source_id"]})
    assert (option["backup_name"], option["backup_eta_min"]) == (backup["name"], backup["eta_min"])
    assert option["needed_by_min"] - backup["eta_min"] <= 180 and option["switch_by_min"] is None, "the backup could not be here in time even if ordered now"
    day = approve(proposal, option)
    req = request_of(day, GASKET)
    assert all(req[k] == option[k] for k in ("needed_by_min", "switch_by_min", "backup_name", "backup_eta_min"))
    assert req["chase"] is None, "with no way back there is nothing to chase until the part is due"
    # a slower source leaves room: the OEM depot is four hours away, the vendor one
    slow = client.post("/api/stalls", json={"ro_id": "RO-1017", "part_id": "TMG-KIT", "force_source": "oem"}).json()["options"][0]
    assert slow["switch_by_min"] == slow["needed_by_min"] - slow["backup_eta_min"] > 180


def test_ordering_the_backup_at_the_switch_by_time_leaves_the_plan_as_it_is():
    day = at_eleven(order_ahead=True)
    req, job = request_of(day, TENSIONER), order_of(day, "RO-1017")
    backup = fastest_other_safe("TMG-TNS", {req["source_id"]})
    clock(req["switch_by_min"])
    r = replan(TENSIONER, cannot_supply=True, force_source=backup["id"])
    assert r.status_code == 200, r.text
    option = r.json()["options"][0]
    assert option["source_id"] == backup["id"] and option["arrives_min"] == req["needed_by_min"]
    assert option["jobs_moved"] == 0 and option["missed_promises"] == 0
    assert (option["stalled_job"]["start_min"], option["stalled_job"]["bay"]) == (job["start_min"], job["bay"])
    clock(req["switch_by_min"] + 15)
    late = replan(TENSIONER, cannot_supply=True, force_source=backup["id"]).json()["options"][0]
    assert late["stalled_job"]["start_min"] > job["start_min"], "one step later, the job can no longer start on time"


def test_a_request_needs_chasing_when_unanswered_or_not_here():
    day = at_eleven(order_ahead=True)
    req = request_of(day, TENSIONER)
    assert req["chase"] is None and day["summary"]["requests_to_chase"] == 0
    day = clock(req["switch_by_min"])
    assert request_of(day, TENSIONER)["chase"] == "no_answer" and day["summary"]["requests_to_chase"] == 1
    day = answer(TENSIONER, "confirmed").json()["day"]
    assert request_of(day, TENSIONER)["chase"] is None and day["summary"]["requests_to_chase"] == 0
    day = clock(req["arrives_min"])
    assert request_of(day, TENSIONER)["chase"] == "not_here", "confirmed is still not the same as here"
    day = answer(TENSIONER, "received").json()["day"]
    assert request_of(day, TENSIONER)["chase"] is None
    # a request that never had a way back is chased from the moment the part is due
    at_eleven()
    option, day = stall_and_approve()
    assert request_of(day, GASKET)["chase"] is None
    assert request_of(clock(option["arrives_min"]), GASKET)["chase"] == "no_answer"


def test_a_new_time_the_plan_can_absorb_is_recorded_and_confirms_the_request():
    day = at_eleven(order_ahead=True)
    req = request_of(day, TENSIONER)
    later = req["arrives_min"] + 15
    assert later <= req["needed_by_min"]
    day = client.post("/api/late/confirm", json={**TENSIONER, "arrives_min": later}).json()["day"]
    req = request_of(day, TENSIONER)
    assert (req["state"], req["arrives_min"]) == ("confirmed", later)


def test_a_source_that_cannot_supply_is_replaced_for_a_car_waiting_in_its_bay():
    at_eleven()
    first, _ = stall_and_approve()
    r = replan(GASKET, cannot_supply=True)
    assert r.status_code == 200, r.text
    proposal = r.json()
    assert (proposal["kind"], proposal["why"], proposal["old_source_id"]) == ("late_part", "cannot_supply", first["source_id"])
    assert not any(s["id"] == first["source_id"] and s["available"] for s in proposal["sources"])
    assert all(o["source_id"] != first["source_id"] and o["backup_name"] != first["source_name"] for o in proposal["options"])
    option = proposal["options"][0]
    was, now = first["stalled_job"], option["stalled_job"]
    assert now["bay"] == was["bay"] and now["start_min"] >= option["arrives_min"]
    assert now["end_min"] - now["start_min"] == was["end_min"] - was["start_min"]
    assert replan(GASKET, cannot_supply=True, force_source=first["source_id"]).status_code == 422, "a source that said no cannot be chosen"
    proposal = replan(GASKET, cannot_supply=True).json()
    option = proposal["options"][0]
    day = approve(proposal, option)
    req = request_of(day, GASKET)
    assert (req["state"], req["source_id"], req["arrives_min"]) == ("requested", option["source_id"], option["arrives_min"])
    assert req["backup_name"] != first["source_name"], "the source that just said no is not offered as the way back"
    hold = [s for s in day["segments"] if s["ro_id"] == "RO-1013" and s["kind"] == "hold"]
    assert len(hold) == 1 and hold[0]["end_min"] == option["stalled_job"]["start_min"]
    shop, jobs, plan, pinned, blocks = repo.load_engine(app_module.conn())
    assert validate(shop, jobs, plan, day["now_min"], plan, pinned=pinned, blocks=blocks)
    log = client.get("/api/log").json()[0]
    assert log["kind"] == "source_switched" and log["detail"]["why"] == "cannot_supply"
    assert (log["detail"]["old_source"], log["detail"]["source"]) == (first["source_name"], option["source_name"])
    by_hand = " ".join(log["detail"]["to_do_by_hand"])
    assert first["source_name"] in by_hand and option["source_name"] in by_hand


def _rank(o):
    return (o["missed_promises"], o["late_minutes"], o["cost"], o["jobs_moved"])


def test_a_new_time_the_plan_cannot_absorb_puts_the_old_source_up_against_the_others():
    at_eleven()
    first, _ = stall_and_approve()
    new_time = first["arrives_min"] + 120
    assert client.post("/api/late/check", json={**GASKET, "arrives_min": new_time}).json()["holds"] is False
    proposal = replan(GASKET, arrives_min=new_time).json()
    assert (proposal["why"], proposal["old_source_id"], proposal["new_arrives_min"]) == ("new_time", first["source_id"], new_time)
    old = next(s for s in proposal["sources"] if s["id"] == first["source_id"])
    assert old["available"] and old["eta_min"] == new_time - 180
    usable = [s for s in proposal["sources"] if s["available"]]
    assert len(usable) >= 3 and all(s["outcome"] for s in usable)
    assert [s["id"] for s in usable if s["why_not"] is None] == [proposal["engine_source_id"]]
    assert _rank(proposal["options"][0]) <= _rank(old["outcome"])
    assert proposal["options"][0]["source_id"] != first["source_id"], "on this day another source gets the part here sooner"
    # the manager may still stay with the source that slipped
    stay = replan(GASKET, arrives_min=new_time, force_source=first["source_id"]).json()
    option = stay["options"][0]
    assert (option["source_id"], option["arrives_min"]) == (first["source_id"], new_time)
    day = approve(stay, option)
    req = request_of(day, GASKET)
    assert (req["state"], req["source_id"], req["arrives_min"]) == ("confirmed", first["source_id"], new_time)
    assert client.get("/api/log").json()[0]["kind"] == "part_late_replanned"
    assert replan(TENSIONER, arrives_min=300).status_code == 409, "nothing is on its way for that job"


def test_with_no_answer_the_current_source_stays_in_the_running_at_its_recorded_time():
    day = at_eleven(order_ahead=True)
    req = request_of(day, PADS_A)
    proposal = replan(PADS_A).json()
    assert proposal["why"] == "no_answer"
    current = next(s for s in proposal["sources"] if s["id"] == req["source_id"])
    assert current["available"] and current["eta_min"] == req["arrives_min"] - 180 and current["outcome"]
    assert replan(PADS_A, force_source="north").status_code == 422, "North has no pads to lend"
    assert replan(PADS_A, arrives_min=req["arrives_min"]).status_code == 409, "a time the plan can absorb is recorded, not re-planned"


def test_a_cancelled_sister_store_gets_its_part_back_unless_it_said_no():
    at_eleven()
    before = on_hand("east", "BRK-PAD-F")
    client.post("/api/precheck/order")
    assert on_hand("east", "BRK-PAD-F") == before - 2, "two jobs were given pads from East"
    day = approve(replan(PADS_A, force_source="vendor").json())
    assert request_of(day, PADS_A)["source_id"] == "vendor" and on_hand("east", "BRK-PAD-F") == before - 1
    proposal = replan(PADS_B, cannot_supply=True).json()
    day = approve(proposal)
    assert request_of(day, PADS_B)["source_id"] != "east" and on_hand("east", "BRK-PAD-F") == before - 1


def test_a_job_taken_apart_without_its_part_is_a_missing_part_that_replaces_the_request():
    day = at_eleven(order_ahead=True)
    start = order_of(day, "RO-1017")["start_min"]
    assert client.post("/api/stalls", json=TENSIONER).status_code == 409, "before the job starts, the part is simply on its way"
    north = on_hand("north", "TMG-TNS")
    clock(start + 15)
    assert replan(TENSIONER, cannot_supply=True).status_code == 409, "the job is under way, so this is no longer a late part"
    r = client.post("/api/stalls", json=TENSIONER)
    assert r.status_code == 200, r.text
    proposal = r.json()
    assert proposal["kind"] == "missing_part" and proposal["in_progress"] is True
    option = proposal["options"][0]
    day = approve(proposal, option)
    req = request_of(day, TENSIONER)
    assert (req["state"], req["source_id"]) == ("requested", option["source_id"])
    assert on_hand("north", "TMG-TNS") == north + 1 - (option["source_id"] == "north"), "the old request is cancelled, so North has its part back"
    # once a part is in the building it cannot be reported missing this way
    day = at_eleven(order_ahead=True)
    answer(TENSIONER, "received")
    clock(start + 15)
    assert client.post("/api/stalls", json=TENSIONER).status_code == 409

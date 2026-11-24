"""API checks against a throwaway database. Run:  .venv/bin/python -m pytest -q"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["STALLBREAKER_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from backend import app as app_module, repo  # noqa: E402
from shopcore import validate  # noqa: E402

client = TestClient(app_module.app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_day_has_a_full_valid_plan():
    day = client.get("/api/day").json()
    assert day["summary"]["orders"] == 40
    assert len(day["technicians"]) == 10 and len(day["bays"]) == 10
    assert all(o["bay"] and o["technician"] for o in day["orders"])
    assert day["summary"]["promises_at_risk"] == 0
    shop, jobs, plan, pinned, blocks = repo.load_engine(app_module.conn())
    assert validate(shop, jobs, plan) and not pinned and not blocks


def test_orders_list_their_parts_and_home_stock():
    day = client.get("/api/day").json()
    pump = [o for o in day["orders"] if o["description"] == "Water pump replacement"]
    assert pump, "the demo day should contain at least one water pump job"
    gasket = [p for p in pump[0]["parts"] if p["part_id"] == "WTR-GSK"][0]
    assert gasket["on_hand_home"] == 0 and pump[0]["short_of_parts"] is True


def test_clock_changes_statuses_but_not_the_plan():
    before = client.get("/api/day").json()
    after = client.post("/api/clock", json={"now_min": 300}).json()
    assert after["now_min"] == 300
    assert [(o["id"], o["start_min"], o["bay"]) for o in before["orders"]] == [(o["id"], o["start_min"], o["bay"]) for o in after["orders"]]
    assert after["summary"]["done"] > before["summary"]["done"]
    assert client.post("/api/clock", json={"now_min": 9999}).status_code == 422


def test_reset_is_repeatable():
    a = client.post("/api/reset").json()["day"]
    b = client.post("/api/reset").json()["day"]
    assert [(o["id"], o["vehicle"], o["promise_min"]) for o in a["orders"]] == [(o["id"], o["vehicle"], o["promise_min"]) for o in b["orders"]]
    assert a["now_min"] == 150


def test_stall_on_a_job_in_progress_offers_sources_and_a_checked_plan():
    client.post("/api/reset")
    p = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"}).json()
    assert p["status"] == "open" and p["in_progress"] is True
    by = {s["id"]: s for s in p["sources"]}
    assert by["north"]["safe"] is False and by["east"]["safe"] is True, "North would be left with none; East has plenty"
    assert by["north"]["risk"] > 0.3 > by["east"]["risk"]
    best = p["options"][0]
    assert best["proven_best"] and best["source_id"] != "north", "an unsafe store is never chosen unless forced"
    assert best["missed_promises"] <= p["no_replan"]["missed_promises"]
    assert best["late_minutes"] < p["no_replan"]["late_minutes"]
    assert best["stalled_job"]["start_min"] >= best["arrives_min"], "work resumes only after the part arrives"
    assert best["stalled_job"]["bay"] == p["current"]["bay"], "a dismantled car stays in its bay"


def test_forcing_a_source_is_honoured_and_rejected_when_impossible():
    client.post("/api/reset")
    forced = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK", "force_source": "north"}).json()
    assert all(o["source_id"] == "north" for o in forced["options"])
    assert client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK", "force_source": "nowhere"}).status_code == 422
    assert client.post("/api/stalls", json={"ro_id": "RO-9999", "part_id": "WTR-GSK"}).status_code == 404
    assert client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "OIL-FLT"}).status_code == 409


def test_approving_a_plan_changes_the_day_and_is_recorded():
    client.post("/api/reset")
    p = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"}).json()
    opt = p["options"][0]
    r = client.post(f"/api/proposals/{p['id']}/approve", json={"option": opt["key"]})
    assert r.status_code == 200
    day = r.json()["day"]
    job = [o for o in day["orders"] if o["id"] == "RO-1013"][0]
    assert job["status"] == "waiting_for_part" and job["start_min"] == opt["stalled_job"]["start_min"]
    assert [p_ for p_ in job["parts"] if p_["part_id"] == "WTR-GSK"][0]["sourced_from"] == opt["source_name"]
    assert {s["kind"] for s in day["segments"] if s["ro_id"] == "RO-1013"} == {"done", "hold"}
    assert day["plan_version"] == p["plan_version"] + 1
    log = client.get("/api/log").json()
    assert log[0]["kind"] == "stall_resolved" and log[0]["detail"]["ro_id"] == "RO-1013"
    # the live plan still obeys every rule, with the stalled job pinned and its bay blocked
    shop, jobs, plan, pinned, blocks = repo.load_engine(app_module.conn())
    assert "RO-1013" in pinned and blocks
    assert validate(shop, jobs, plan, day["now_min"], plan, pinned=pinned, blocks=blocks)
    # the same proposal cannot be approved twice, and the part cannot be reported again
    assert client.post(f"/api/proposals/{p['id']}/approve", json={"option": opt["key"]}).status_code == 409
    assert client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"}).status_code == 409


def test_a_second_stall_plans_around_the_first():
    client.post("/api/reset")
    p = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"}).json()
    client.post(f"/api/proposals/{p['id']}/approve", json={"option": p["options"][0]["key"]})
    day = client.get("/api/day").json()
    later = [o for o in day["orders"] if o["status"] == "scheduled" and o["parts"]][0]
    q = client.post("/api/stalls", json={"ro_id": later["id"], "part_id": later["parts"][0]["part_id"]}).json()
    assert q["in_progress"] is False and q["options"]
    first = [o for o in day["orders"] if o["id"] == "RO-1013"][0]
    for opt in q["options"]:
        a = opt["assignments"]["RO-1013"]
        assert (a["start_min"], a["bay"]) == (first["start_min"], first["bay"]), "the first stalled job must not move"
        assert opt["stalled_job"]["start_min"] >= opt["arrives_min"]
    r = client.post(f"/api/proposals/{q['id']}/approve", json={"option": q["options"][-1]["key"]})
    assert r.status_code == 200
    shop, jobs, plan, pinned, blocks = repo.load_engine(app_module.conn())
    assert validate(shop, jobs, plan, day["now_min"], plan, pinned=pinned, blocks=blocks)


def test_a_stale_proposal_cannot_be_approved():
    client.post("/api/reset")
    a = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"}).json()
    b = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK", "force_source": "east"}).json()
    assert client.post(f"/api/proposals/{a['id']}/approve", json={"option": a["options"][0]["key"]}).status_code == 409
    assert client.get(f"/api/proposals/{b['id']}").json()["status"] == "open"
    assert client.post(f"/api/proposals/{b['id']}/dismiss").status_code == 200
    assert client.get(f"/api/proposals/{b['id']}").json()["status"] == "dismissed"


def test_parts_check_finds_shortfalls_and_says_which_can_be_fixed_quietly():
    client.post("/api/reset")
    chk = client.get("/api/precheck").json()
    flagged = {(f["ro_id"], f["part_id"]): f for f in chk["flagged"]}
    assert chk["fixable_without_replan"] + chk["need_a_decision"] == len(flagged) >= 3
    started = flagged[("RO-1013", "WTR-GSK")]
    assert started["already_started"] and started["fix"] is None and started["reason"] == "out_of_stock"
    for f in chk["flagged"]:
        if f["fix"]:
            assert f["fix"]["arrives_min"] <= f["start_min"], "a quiet fix must arrive before the job starts"
    # stock is handed out in start order: a part can be on the shelf and still not reach a later job
    assert any(f["reason"] == "claimed_by_earlier_jobs" for f in chk["flagged"])


def test_ordering_ahead_fixes_jobs_without_touching_the_schedule():
    client.post("/api/reset")
    before = client.get("/api/day").json()
    chk = client.get("/api/precheck").json()
    r = client.post("/api/precheck/order").json()
    assert len(r["placed"]) == chk["fixable_without_replan"] > 0
    after = r["day"]
    assert [(o["id"], o["start_min"], o["bay"], o["technician"]) for o in before["orders"]] == [(o["id"], o["start_min"], o["bay"], o["technician"]) for o in after["orders"]]
    assert r["precheck"]["fixable_without_replan"] == 0
    assert sum(o["short_of_parts"] for o in after["orders"]) == sum(o["short_of_parts"] for o in before["orders"]) - len({p["ro_id"] for p in r["placed"]})
    assert client.get("/api/log").json()[0]["kind"] == "parts_ordered_ahead"
    assert client.post("/api/precheck/order").json()["placed"] == [], "ordering twice must not order anything again"


def test_a_late_part_within_the_spare_time_changes_nothing():
    client.post("/api/reset")
    r = client.post("/api/precheck/order").json()
    job = r["placed"][0]
    spare = job["job_starts_min"] - job["arrives_min"]
    order = [o for o in r["day"]["orders"] if o["id"] == job["ro_id"]][0]
    part_id = [p["part_id"] for p in order["parts"] if p["sourced_from"]][0]
    ok = client.post("/api/late/check", json={"ro_id": job["ro_id"], "part_id": part_id, "arrives_min": job["job_starts_min"]}).json()
    assert ok["holds"] is True and ok["spare_min"] == 0 and spare >= 0
    done = client.post("/api/late/confirm", json={"ro_id": job["ro_id"], "part_id": part_id, "arrives_min": job["job_starts_min"]})
    assert done.status_code == 200
    again = [o for o in done.json()["day"]["orders"] if o["id"] == job["ro_id"]][0]
    assert again["start_min"] == order["start_min"]
    assert [p["arrives_min"] for p in again["parts"] if p["sourced_from"]] == [job["job_starts_min"]]
    # past the spare time it is no longer a simple confirmation
    assert client.post("/api/late/confirm", json={"ro_id": job["ro_id"], "part_id": part_id, "arrives_min": job["job_starts_min"] + 60}).status_code == 409


def test_a_late_part_for_a_dismantled_car_extends_the_blocked_bay():
    client.post("/api/reset")
    p = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"}).json()
    first = p["options"][0]
    client.post(f"/api/proposals/{p['id']}/approve", json={"option": first["key"]})
    new_arrival = first["arrives_min"] + 60
    late = client.post("/api/late/check", json={"ro_id": "RO-1013", "part_id": "WTR-GSK", "arrives_min": new_arrival}).json()
    assert late["holds"] is False and late["proposal"]["kind"] == "late_part"
    opt = late["proposal"]["options"][0]
    assert opt["stalled_job"]["start_min"] >= new_arrival and opt["stalled_job"]["bay"] == first["stalled_job"]["bay"]
    assert opt["stalled_job"]["end_min"] - opt["stalled_job"]["start_min"] == first["stalled_job"]["end_min"] - first["stalled_job"]["start_min"]
    day = client.post(f"/api/proposals/{late['proposal']['id']}/approve", json={"option": opt["key"]}).json()["day"]
    hold = [s for s in day["segments"] if s["ro_id"] == "RO-1013" and s["kind"] == "hold"][0]
    assert hold["end_min"] == opt["stalled_job"]["start_min"]
    assert client.get("/api/log").json()[0]["kind"] == "part_late_replanned"
    shop, jobs, plan, pinned, blocks = repo.load_engine(app_module.conn())
    assert validate(shop, jobs, plan, day["now_min"], plan, pinned=pinned, blocks=blocks)
    assert client.post("/api/late/check", json={"ro_id": "RO-1001", "part_id": "OIL-FLT", "arrives_min": 300}).status_code == 409


# --- spec 107: why not this source? ---

def _rank(o):
    """The engine's own goal order for the recommended plan."""
    return (o["missed_promises"], o["late_minutes"], o["cost"], o["jobs_moved"])


def test_every_source_says_what_the_day_would_look_like():
    client.post("/api/reset")
    p = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"}).json()
    best = p["options"][0]
    assert p["engine_source_id"] == best["source_id"]
    for s in p["sources"]:
        if not s["available"]:
            assert s["outcome"] is None and s["why_not"] is None
            continue
        o = s["outcome"]
        assert o["arrives_min"] == p["now_min"] + s["eta_min"] and o["cost"] == s["cost"]
        if s["id"] == best["source_id"]:
            assert s["why_not"] is None
            assert _rank(o) == _rank(best) and o["bay_blocked_min"] == best["bay_blocked_min"]
        else:
            assert s["why_not"], f"{s['name']} was not chosen and must say why"
            if s["safe"]:
                assert _rank(o) >= _rank(best), "no safe source may beat the one the engine chose"
    by = {s["id"]: s for s in p["sources"]}
    assert "unsafe" in by["north"]["why_not"].lower()
    # the reason names the first goal the source loses on
    depot = by["oem"]
    if depot["outcome"]["missed_promises"] > best["missed_promises"]:
        assert "promise" in depot["why_not"]


def test_forcing_a_source_still_names_the_engines_pick():
    client.post("/api/reset")
    free = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"}).json()
    forced = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK", "force_source": "north"}).json()
    assert forced["options"][0]["source_id"] == "north"
    assert forced["engine_source_id"] == free["engine_source_id"] != "north"


def test_a_proposal_comes_back_within_five_seconds():
    import time
    client.post("/api/reset")
    t0 = time.perf_counter()
    r = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"})
    assert r.status_code == 200 and time.perf_counter() - t0 < 5.0


# --- spec 108: how late can the part be? ---

def test_a_plan_says_how_late_the_part_can_be():
    client.post("/api/reset")
    p = client.post("/api/stalls", json={"ro_id": "RO-1013", "part_id": "WTR-GSK"}).json()
    opt = p["options"][0]
    margin = opt["late_margin_min"]
    assert margin % 15 == 0 and 0 <= margin <= 240
    assert opt["late_margin_capped"] is (margin == 240)
    client.post(f"/api/proposals/{p['id']}/approve", json={"option": opt["key"]})

    def missed_if_late_by(extra):
        r = client.post("/api/late/check", json={"ro_id": "RO-1013", "part_id": "WTR-GSK", "arrives_min": opt["arrives_min"] + extra}).json()
        return opt["missed_promises"] if r["holds"] else r["proposal"]["options"][0]["missed_promises"]

    assert missed_if_late_by(margin) <= opt["missed_promises"], "inside the margin no extra promise is lost"
    if not opt["late_margin_capped"]:
        assert missed_if_late_by(margin + 15) > opt["missed_promises"], "one step past the margin costs a promise"

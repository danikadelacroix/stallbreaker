"""Checks on reading a technician's note (spec 112). Run:  .venv/bin/python -m pytest -q"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("STALLBREAKER_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
os.environ["OPENROUTER_API_KEY"] = os.environ["LLM_MODEL"] = ""  # tests never call a real model, whatever is in .env

from fastapi.testclient import TestClient  # noqa: E402

from backend import app as app_module, intake, llm  # noqa: E402

client = TestClient(app_module.app)


def at_eleven(order_ahead=False):
    client.post("/api/reset")
    client.post("/api/clock", json={"now_min": 180})
    if order_ahead:
        client.post("/api/precheck/order")


def read(text):
    r = client.post("/api/intake", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


def test_a_shorthand_note_is_read_to_the_right_job_and_part():
    at_eleven()
    note = "1013 wp off, gskt kit in bin is for the 2.0 not 2.5t"
    got = read(note)
    assert (got["kind"], got["ro_id"], got["part_id"]) == ("missing_part", "RO-1013", "WTR-GSK")
    assert got["part_name"] == "Water pump gasket kit" and got["vehicle"] == "2020 Ford Explorer"
    assert got["quote"] == "gskt kit in bin is for the 2.0 not 2.5t", "a decimal point does not end the sentence"
    assert got["read_by"] == "rules" and got["why_unclear"] is None
    by_bay = read("bay 7 explorer - need water pump gasket set, none in stock")
    assert (by_bay["ro_id"], by_bay["part_id"]) == ("RO-1013", "WTR-GSK"), "no number: found by bay and vehicle"


def test_reading_a_note_changes_nothing():
    at_eleven()
    before, log_before = client.get("/api/day").json(), client.get("/api/log").json()
    read("1013 wp off, gskt kit in bin is for the 2.0 not 2.5t")
    after = client.get("/api/day").json()
    assert after == before and after["open_proposal_id"] is None and client.get("/api/log").json() == log_before


def test_a_note_that_cannot_be_read_says_why():
    at_eleven()
    for note, word in (("9999 needs a water pump", "repair order"), ("1013 thermostat housing bolt snapped, need 1", "part"),
                       ("1026 done, corolla ready for pickup", ""), ("explorer needs a part", "")):
        got = read(note)
        assert got["kind"] == "unclear" and got["why_unclear"], note
        assert word in got["why_unclear"]
    assert client.post("/api/intake", json={"text": ""}).status_code == 422
    assert client.post("/api/intake", json={"text": "x" * 601}).status_code == 422


def test_a_note_about_a_late_part_is_read_with_its_new_time():
    at_eleven(order_ahead=True)
    got = read("north says tensioner for 1017 wont be here till 12:30")
    assert (got["kind"], got["ro_id"], got["part_id"], got["arrives_min"]) == ("late_part", "RO-1017", "TMG-TNS", 270)
    at_eleven()  # nothing was ordered, so nothing can be late
    assert read("north says tensioner for 1017 wont be here till 12:30")["kind"] != "late_part"


class StandIn:
    """Takes the place of a real model in tests. Returns whatever it was told to."""
    name = "stand-in"

    def __init__(self, answer):
        self.answer, self.sent = answer, []

    def __call__(self, system, user, schema):
        self.sent.append(user)
        return self.answer


def test_a_wrong_model_answer_is_thrown_away_and_the_fallback_is_named(monkeypatch):
    at_eleven()
    note = "1013 wp off, gskt kit in bin is for the 2.0 not 2.5t"
    wrong = [
        {"kind": "missing_part", "ro_id": "RO-4242", "part_id": "WTR-GSK", "arrives_min": None, "quote": "gskt kit"},  # no such order
        {"kind": "missing_part", "ro_id": "RO-1013", "part_id": "BAT-H6", "arrives_min": None, "quote": "gskt kit"},   # not a part of this job
        {"kind": "missing_part", "ro_id": "RO-1013", "part_id": "WTR-GSK", "arrives_min": None, "quote": "the kit is missing"},  # words not in the note
        None,                                                                                                              # no answer at all
    ]
    for answer in wrong:
        monkeypatch.setattr(llm, "reader", lambda a=answer: StandIn(a))
        got = read(note)
        assert got["read_by"] == "rules" and got["fell_back_because"], answer
        assert (got["ro_id"], got["part_id"]) == ("RO-1013", "WTR-GSK")


def test_a_good_model_answer_is_used_and_labelled(monkeypatch):
    at_eleven()
    note = "the explorer Pooja is on has no gasket kit"
    good = StandIn({"kind": "missing_part", "ro_id": "RO-1013", "part_id": "WTR-GSK", "arrives_min": None, "quote": "has no gasket kit"})
    monkeypatch.setattr(llm, "reader", lambda: good)
    got = read(note)
    assert got["read_by"] == "model: stand-in" and got["fell_back_because"] is None
    assert (got["kind"], got["ro_id"], got["part_id"], got["quote"]) == ("missing_part", "RO-1013", "WTR-GSK", "has no gasket kit")
    assert "RO-1013" in good.sent[0] and "WTR-GSK" in good.sent[0], "the model is given the lists it must choose from"


def test_personal_details_are_removed_before_a_note_is_sent(monkeypatch):
    at_eleven()
    seen = StandIn(None)
    monkeypatch.setattr(llm, "reader", lambda: seen)
    read("1013 no gasket kit. customer Rick 555-201-8890 rick@example.com vin 1FM5K8D86LGA12345 wants a call")
    sent = seen.sent[0]
    assert "555-201-8890" not in sent and "rick@example.com" not in sent and "1FM5K8D86LGA12345" not in sent
    assert "gasket kit" in sent


def test_the_published_score_matches_the_rules_reader():
    cases = [json.loads(l) for l in open(os.path.join(ROOT, "tests", "intake_cases.jsonl"))]
    assert len(cases) >= 70 and {c["split"] for c in cases} == {"dev", "held_out", "outside"}
    published = json.load(open(os.path.join(ROOT, "experiments", "out", "intake_eval.json")))["rules"]
    at_eleven(order_ahead=True)
    right = {"dev": 0, "held_out": 0, "outside": 0}
    for c in cases:
        got = intake.read_with_rules(app_module.conn(), c["text"])
        right[c["split"]] += intake.same_reading(got, c)
    assert all(published[s]["right"] == right[s] for s in right)
    assert right["outside"] < published["outside"]["of"], "if this ever reads every outside note, suspect that someone tuned on them"
    info = client.get("/api/intake/info").json()
    assert info["reader"] == "rules" and info["sends_notes_out"] is False and info["eval"]["rules"]["outside"]["right"] == right["outside"]

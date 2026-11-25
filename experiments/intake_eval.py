"""How well does a reader turn technicians' notes into the right repair order and part?

Run:  .venv/bin/python experiments/intake_eval.py            (the rules reader)
      .venv/bin/python experiments/intake_eval.py --live     (also the model set up in .env)
Writes experiments/out/intake_eval.json and intake_eval.md.

The notes are in tests/intake_cases.jsonl, in three groups. 'dev' and 'held_out' were written by the
project's authors, who also wrote the reading rules, so those scores flatter the rules reader; the
rules may be tuned on 'dev' only. 'outside' was written by someone who saw only the day's jobs and
parts, never the rules or the other notes. It is frozen: nothing is ever tuned on it, and it is the
score to quote.
"""
import datetime
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["STALLBREAKER_DB"] = os.path.join(tempfile.mkdtemp(), "eval.db")

from backend import db, intake, llm, precheck, seed  # noqa: E402

OUT = os.path.join(ROOT, "experiments", "out")
CLOCK = 180  # 11:00, after the parts that can be ordered ahead have been ordered
SPLITS = ("dev", "held_out", "outside")


def demo_day():
    conn = db.connect()
    seed.build(conn)
    db.set_meta(conn, "now_min", CLOCK)
    precheck.order_fixes(conn)
    return conn


def score(read, cases):
    result = {s: {"right": 0, "of": 0} for s in SPLITS}
    result.update(wrong=[], outside_misses={"said_unclear": 0, "read_it_wrong": 0, "opened_a_note_it_should_not": 0})
    for c in cases:
        got = read(c["text"])
        ok = intake.same_reading(got, c)
        result[c["split"]]["right"] += ok
        result[c["split"]]["of"] += 1
        if not ok and c["split"] == "outside":  # counted by kind only, so nobody is tempted to tune on them
            kind = "said_unclear" if got["kind"] == "unclear" else "opened_a_note_it_should_not" if c["kind"] == "unclear" else "read_it_wrong"
            result["outside_misses"][kind] += 1
        elif not ok:
            result["wrong"].append({"id": c["id"], "split": c["split"], "text": c["text"], "expected": [c["kind"], c["ro_id"], c["part_id"], c["arrives_min"]],
                                    "got": [got["kind"], got["ro_id"], got["part_id"], got["arrives_min"]]})
    return result


def main():
    conn = demo_day()
    cases = [json.loads(line) for line in open(os.path.join(ROOT, "tests", "intake_cases.jsonl"))]
    results = {"rules": score(lambda t: intake.read_with_rules(conn, t), cases)}
    if "--live" in sys.argv:
        ask = llm.reader()
        if ask is None:
            sys.exit("No model is set up. Put OPENROUTER_API_KEY and LLM_MODEL in .env first.")

        def with_model(text):
            reading, _why = intake._from_model(conn, ask(intake.SYSTEM, intake._question(conn, text), intake.SCHEMA), text)
            return reading or intake._unclear("no usable answer")
        results[f"model: {ask.name}"] = {**score(with_model, cases), "run_on": datetime.date.today().isoformat()}
    else:  # keep any model score from an earlier live run
        path = os.path.join(OUT, "intake_eval.json")
        if os.path.exists(path):
            results.update({k: v for k, v in json.load(open(path)).items() if k.startswith("model: ")})
    os.makedirs(OUT, exist_ok=True)
    json.dump(results, open(os.path.join(OUT, "intake_eval.json"), "w"), indent=1)
    lines = ["# Reading technicians' notes", "",
             f"{len(cases)} notes, read on the demo day at 11:00. A reading is right only if the repair order, the part and",
             "any new arrival time all match, or if a note that cannot be read comes out as unclear.", "",
             "| Reader | Our notes, used for tuning | Our notes, held out | Notes written by someone else |", "|---|---|---|---|"]
    for name, r in results.items():
        lines.append(f"| {name} | {r['dev']['right']} of {r['dev']['of']} | {r['held_out']['right']} of {r['held_out']['of']} | "
                     f"**{r['outside']['right']} of {r['outside']['of']}** |")
    lines += ["", "The first two columns flatter the rules reader: the same people wrote those notes and the rules. The last",
              "column is the one to quote. Those notes were written by someone who saw only the day's jobs and parts, and",
              "nothing is ever tuned on them.", ""]
    for name, r in results.items():
        m = r["outside_misses"]
        lines.append(f"- {name}, misses on outside notes: said 'unclear' {m['said_unclear']} times (safe: a person picks the job by hand), "
                     f"read the wrong job, part or time {m['read_it_wrong']} times, and offered to open a note it should not have "
                     f"{m['opened_a_note_it_should_not']} times (a person has to catch these on the confirm card).")
    for name, r in results.items():
        for w in r["wrong"]:
            lines.append(f"- {name} got note {w['id']} wrong ({w['split']}): \"{w['text']}\" expected {w['expected']}, got {w['got']}")
    text = "\n".join(lines)
    open(os.path.join(OUT, "intake_eval.md"), "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()

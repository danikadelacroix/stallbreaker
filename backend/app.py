"""StallBreaker API. Run from the repo root:  .venv/bin/python -m uvicorn backend.app:app --port 8000"""
import functools
import os
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db, intake, precheck, repo, seed, stalls

app = FastAPI(title="StallBreaker", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

_conn = None
_lock = threading.RLock()


def one_at_a_time(handler):
    """Requests share one database connection and the solver, so they run one after another."""
    @functools.wraps(handler)
    def wrapped(*args, **kwargs):
        with _lock:
            return handler(*args, **kwargs)
    return wrapped


def conn():
    """One shared connection. The database is created and seeded on first use."""
    global _conn
    if _conn is None:
        fresh = not os.path.exists(db.DB_PATH)
        _conn = db.connect()
        if fresh or _conn.execute("SELECT COUNT(*) FROM repair_orders").fetchone()[0] == 0:
            seed.build(_conn)
    return _conn


class Clock(BaseModel):
    now_min: int = Field(ge=0, le=600, description="Minutes after 08:00")


class StallReport(BaseModel):
    ro_id: str = Field(pattern=r"^RO-\d{1,6}$")
    part_id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Z0-9-]+$")
    force_source: str | None = Field(default=None, max_length=20, pattern=r"^[a-z]+$")
    force_bay: str | None = Field(default=None, pattern=r"^(hold|roll_out)$", description="Keep the car in its bay, or roll it out, whatever the engine advises")


class LatePart(BaseModel):
    ro_id: str = Field(pattern=r"^RO-\d{1,6}$")
    part_id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Z0-9-]+$")
    arrives_min: int = Field(ge=0, le=900, description="New arrival time, minutes after 08:00")


class Replan(BaseModel):
    ro_id: str = Field(pattern=r"^RO-\d{1,6}$")
    part_id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Z0-9-]+$")
    arrives_min: int | None = Field(default=None, ge=0, le=900, description="The new arrival time the source gave, if it gave one")
    cannot_supply: bool = Field(default=False, description="The source said it cannot supply the part")
    force_source: str | None = Field(default=None, max_length=20, pattern=r"^[a-z]+$")


class Answer(BaseModel):
    ro_id: str = Field(pattern=r"^RO-\d{1,6}$")
    part_id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Z0-9-]+$")
    answer: str = Field(pattern=r"^(confirmed|received)$")


class Note(BaseModel):
    text: str = Field(min_length=1, max_length=600, description="What the technician typed or said")


class Approval(BaseModel):
    option: str = Field(pattern=r"^[a-z_]{1,30}$")


def _guard(work):
    """Turn the stall flow's own errors into HTTP errors with a readable message."""
    try:
        return work()
    except stalls.StallError as e:
        raise HTTPException(status_code=e.status, detail=e.message)


@app.get("/api/health")
@one_at_a_time
def health():
    import ortools
    return {"ok": True, "solver": f"OR-Tools {ortools.__version__}"}


@app.get("/api/day")
@one_at_a_time
def get_day():
    return repo.day(conn())


@app.post("/api/clock")
@one_at_a_time
def set_clock(body: Clock):
    """Move the demo clock. The plan does not change; only what counts as done, running or still to come."""
    if db.get_meta(conn(), "now_min", 0) != body.now_min:
        db.set_meta(conn(), "now_min", body.now_min)
        db.bump_plan_version(conn())  # a plan drafted at another time of day must not be approved
    return repo.day(conn())


@app.post("/api/reset")
@one_at_a_time
def reset(seed_value: int = seed.DEFAULT_SEED):
    """Rebuild the demo day from scratch."""
    if not 0 <= seed_value <= 10**6:
        raise HTTPException(status_code=422, detail="seed_value must be between 0 and 1,000,000")
    info = seed.build(conn(), seed=seed_value)
    return {"reset": info, "day": repo.day(conn())}


@app.get("/api/log")
@one_at_a_time
def log():
    import json
    return [{"id": r["id"], "at_min": r["at_min"], "kind": r["kind"], "detail": json.loads(r["detail"])}
            for r in conn().execute("SELECT * FROM audit_log ORDER BY id DESC")]


@app.post("/api/stalls")
@one_at_a_time
def report_stall(body: StallReport):
    """A part is missing for a repair order. Returns the sources and the plan options."""
    return _guard(lambda: stalls.propose(conn(), body.ro_id, body.part_id, body.force_source, body.force_bay))


@app.get("/api/proposals/{proposal_id}")
@one_at_a_time
def get_proposal(proposal_id: int):
    return _guard(lambda: stalls.get(conn(), proposal_id))


@app.post("/api/proposals/{proposal_id}/approve")
@one_at_a_time
def approve_proposal(proposal_id: int, body: Approval):
    decided = _guard(lambda: stalls.approve(conn(), proposal_id, body.option))
    return {"decided": decided, "day": repo.day(conn())}


@app.post("/api/proposals/{proposal_id}/dismiss")
@one_at_a_time
def dismiss_proposal(proposal_id: int):
    _guard(lambda: stalls.dismiss(conn(), proposal_id))
    return repo.day(conn())


@app.post("/api/intake")
@one_at_a_time
def read_note(body: Note):
    """Read a technician's note into a repair order and a part. Saves nothing: a person confirms the reading first."""
    return intake.read(conn(), body.text)


@app.get("/api/intake/info")
@one_at_a_time
def intake_info():
    """Which reader is in use, whether notes leave the machine, and how the reader scored on the test notes."""
    return intake.info()


@app.get("/api/precheck")
@one_at_a_time
def get_precheck():
    """Jobs that will be short of a part, and whether each can be fixed without touching the schedule."""
    return precheck.run(conn())


@app.post("/api/precheck/order")
@one_at_a_time
def order_precheck():
    """Order every part that can arrive before its job starts."""
    placed = precheck.order_fixes(conn())
    return {"placed": placed, "precheck": precheck.run(conn()), "day": repo.day(conn())}


@app.post("/api/late/check")
@one_at_a_time
def check_late_part(body: LatePart):
    """A part on its way will arrive at a new time. Says whether the plan holds. Saves nothing."""
    return _guard(lambda: stalls.check_late(conn(), body.ro_id, body.part_id, body.arrives_min))


@app.post("/api/late/replan")
@one_at_a_time
def replan_late_part(body: Replan):
    """The source slipped, said no, or has not answered: plan the day again with every source in the running."""
    return _guard(lambda: stalls.replan_late(conn(), body.ro_id, body.part_id, body.arrives_min, body.cannot_supply, body.force_source))


@app.post("/api/requests/answer")
@one_at_a_time
def answer_request(body: Answer):
    """Record that a source confirmed a part, or that the part has been received. The plan is not touched."""
    _guard(lambda: stalls.answer(conn(), body.ro_id, body.part_id, body.answer))
    return {"day": repo.day(conn())}


@app.post("/api/late/confirm")
@one_at_a_time
def confirm_late_part(body: LatePart):
    """Record a new arrival time that the plan can absorb without changes."""
    result = _guard(lambda: stalls.confirm_late(conn(), body.ro_id, body.part_id, body.arrives_min))
    return {"result": result, "day": repo.day(conn())}

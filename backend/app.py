"""StallBreaker API. Run from the repo root:  .venv/bin/python -m uvicorn backend.app:app --port 8000"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db, precheck, repo, seed, stalls

app = FastAPI(title="StallBreaker", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

_conn = None


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


class LatePart(BaseModel):
    ro_id: str = Field(pattern=r"^RO-\d{1,6}$")
    part_id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Z0-9-]+$")
    arrives_min: int = Field(ge=0, le=900, description="New arrival time, minutes after 08:00")


class Approval(BaseModel):
    option: str = Field(pattern=r"^[a-z_]{1,30}$")


def _guard(work):
    """Turn the stall flow's own errors into HTTP errors with a readable message."""
    try:
        return work()
    except stalls.StallError as e:
        raise HTTPException(status_code=e.status, detail=e.message)


@app.get("/api/health")
def health():
    import ortools
    return {"ok": True, "solver": f"OR-Tools {ortools.__version__}"}


@app.get("/api/day")
def get_day():
    return repo.day(conn())


@app.post("/api/clock")
def set_clock(body: Clock):
    """Move the demo clock. The plan does not change; only what counts as done, running or still to come."""
    db.set_meta(conn(), "now_min", body.now_min)
    return repo.day(conn())


@app.post("/api/reset")
def reset(seed_value: int = seed.DEFAULT_SEED):
    """Rebuild the demo day from scratch."""
    if not 0 <= seed_value <= 10**6:
        raise HTTPException(status_code=422, detail="seed_value must be between 0 and 1,000,000")
    info = seed.build(conn(), seed=seed_value)
    return {"reset": info, "day": repo.day(conn())}


@app.get("/api/log")
def log():
    import json
    return [{"id": r["id"], "at_min": r["at_min"], "kind": r["kind"], "detail": json.loads(r["detail"])}
            for r in conn().execute("SELECT * FROM audit_log ORDER BY id DESC")]


@app.post("/api/stalls")
def report_stall(body: StallReport):
    """A part is missing for a repair order. Returns the sources and the plan options."""
    return _guard(lambda: stalls.propose(conn(), body.ro_id, body.part_id, body.force_source))


@app.get("/api/proposals/{proposal_id}")
def get_proposal(proposal_id: int):
    return _guard(lambda: stalls.get(conn(), proposal_id))


@app.post("/api/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: int, body: Approval):
    decided = _guard(lambda: stalls.approve(conn(), proposal_id, body.option))
    return {"decided": decided, "day": repo.day(conn())}


@app.post("/api/proposals/{proposal_id}/dismiss")
def dismiss_proposal(proposal_id: int):
    _guard(lambda: stalls.dismiss(conn(), proposal_id))
    return repo.day(conn())


@app.get("/api/precheck")
def get_precheck():
    """Jobs that will be short of a part, and whether each can be fixed without touching the schedule."""
    return precheck.run(conn())


@app.post("/api/precheck/order")
def order_precheck():
    """Order every part that can arrive before its job starts."""
    placed = precheck.order_fixes(conn())
    return {"placed": placed, "precheck": precheck.run(conn()), "day": repo.day(conn())}


@app.post("/api/late/check")
def check_late_part(body: LatePart):
    """A part on its way will arrive at a new time. Says whether the plan holds, or returns new plans."""
    return _guard(lambda: stalls.check_late(conn(), body.ro_id, body.part_id, body.arrives_min))


@app.post("/api/late/confirm")
def confirm_late_part(body: LatePart):
    """Record a new arrival time that the plan can absorb without changes."""
    result = _guard(lambda: stalls.confirm_late(conn(), body.ro_id, body.part_id, body.arrives_min))
    return {"result": result, "day": repo.day(conn())}

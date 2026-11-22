"""SQLite storage for the prototype. One file, plain SQL, no ORM."""
import json
import os
import sqlite3

DB_PATH = os.environ.get("STALLBREAKER_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "stallbreaker.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS stores (id TEXT PRIMARY KEY, name TEXT NOT NULL, is_home INTEGER NOT NULL, shuttle_minutes INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS suppliers (id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, lead_minutes INTEGER NOT NULL, surcharge REAL NOT NULL);
CREATE TABLE IF NOT EXISTS technicians (id TEXT PRIMARY KEY, name TEXT NOT NULL, skills TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bays (id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS parts (id TEXT PRIMARY KEY, name TEXT NOT NULL, unit_cost REAL NOT NULL, series_id TEXT);
CREATE TABLE IF NOT EXISTS stock (store_id TEXT NOT NULL, part_id TEXT NOT NULL, on_hand INTEGER NOT NULL, PRIMARY KEY (store_id, part_id));
CREATE TABLE IF NOT EXISTS job_types (code TEXT PRIMARY KEY, description TEXT NOT NULL, minutes INTEGER NOT NULL, skill TEXT NOT NULL, bay_kinds TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS job_type_parts (code TEXT NOT NULL, part_id TEXT NOT NULL, qty INTEGER NOT NULL, PRIMARY KEY (code, part_id));
CREATE TABLE IF NOT EXISTS repair_orders (
  id TEXT PRIMARY KEY, vehicle TEXT NOT NULL, job_code TEXT NOT NULL, description TEXT NOT NULL, minutes INTEGER NOT NULL,
  skill TEXT NOT NULL, bay_kinds TEXT NOT NULL, release_min INTEGER NOT NULL, promise_min INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS ro_parts (ro_id TEXT NOT NULL, part_id TEXT NOT NULL, qty INTEGER NOT NULL, PRIMARY KEY (ro_id, part_id));
CREATE TABLE IF NOT EXISTS assignments (ro_id TEXT PRIMARY KEY, start_min INTEGER NOT NULL, end_min INTEGER NOT NULL, tech_id TEXT NOT NULL, bay_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, at_min INTEGER NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
-- A proposal is the set of plan options offered for one stall, kept so a refresh or a second browser sees the same thing.
CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY AUTOINCREMENT, created_min INTEGER NOT NULL, plan_version INTEGER NOT NULL,
  ro_id TEXT NOT NULL, part_id TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL);
-- Extra pieces of a stalled job: the work done before the stall, and the time its bay is blocked waiting for the part.
CREATE TABLE IF NOT EXISTS segments (id INTEGER PRIMARY KEY AUTOINCREMENT, ro_id TEXT NOT NULL, kind TEXT NOT NULL,
  start_min INTEGER NOT NULL, end_min INTEGER NOT NULL, tech_id TEXT, bay_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sourced (ro_id TEXT NOT NULL, part_id TEXT NOT NULL, source_id TEXT NOT NULL, source_name TEXT NOT NULL,
  arrives_min INTEGER NOT NULL, cost REAL NOT NULL, PRIMARY KEY (ro_id, part_id));
"""
TABLES = ["stores", "suppliers", "technicians", "bays", "parts", "stock", "job_types", "job_type_parts",
          "repair_orders", "ro_parts", "assignments", "meta", "audit_log", "proposals", "segments", "sourced"]


def connect(path=None):
    conn = sqlite3.connect(path or DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def wipe(conn):
    for t in TABLES:
        conn.execute(f"DELETE FROM {t}")
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('audit_log', 'proposals', 'segments')")
    conn.commit()


def get_meta(conn, key, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_meta(conn, key, value):
    conn.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, json.dumps(value)))
    conn.commit()

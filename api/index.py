"""Entry point for the hosted copy (Vercel). The same FastAPI app as local runs, with its database in the one writable folder."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("STALLBREAKER_DB", "/tmp/stallbreaker.db")  # serverless disks are read-only except /tmp

from backend.app import app  # noqa: E402,F401

"""Vercel entry point. One Python function serves the GigBid API, the in-process GigSim and
MCP servers, and the built web app (apps/web/dist), all on one origin."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("INPROC_SERVICES", "1")
os.environ.setdefault("MCP_TRANSPORT", "inproc")
os.environ.setdefault("GIGSIM_BASE_URL", "inproc")
os.environ.setdefault("GIGBID_MODEL_DIR", "/tmp/models")
os.environ.setdefault("GIGBID_LEDGER_PG", "1")
os.environ.setdefault("HF_HOME", "/tmp/hf")

from apps.api.main import app  # noqa: E402,F401

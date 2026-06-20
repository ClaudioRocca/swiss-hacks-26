"""FastAPI WebSocket server — streams live transcription + concept triggers to the frontend.

Supports two modes:
  1. audio — upload an MP3 (or use the default), run through real STT pipeline
  2. text  — feed a scripted .txt file through the segmenter (fast, no STT needed)

WebSocket protocol (server → client):
  {"type": "partial", "text": "..."}           — growing partial transcript
  {"type": "final", "text": "..."}             — finalized utterance
  {"type": "concept", "topic": "...", ...}     — concept with executed query results
  {"type": "done"}                             — pipeline finished
  {"type": "error", "message": "..."}          — something broke

WebSocket protocol (client → server):
  {"type": "start"}                            — start with default file (text mode)
  {"type": "start", "file": "path.txt"}        — start with a specific text file
  {"type": "start", "file": "path.mp3", "mode": "audio"}  — real STT mode
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from speech-to-text/ first, then fall back to parent (swiss-hacks-26/.env)
_here = Path(__file__).parent
load_dotenv(_here / ".env")
load_dotenv(_here.parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent))

from src.agent.segmenter import ConceptChunk, DataRequest
from src.data import DataLayerError, db
from src.orchestrator import run_file, run_text

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="RM Compass — Live Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon: allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Query execution (adapted from run_pipeline_execute.py)
# ---------------------------------------------------------------------------

_SENTINEL = "all"
_DATE_KEYS = {"since", "until"}
_ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

_SOURCES: dict[str, dict[str, Any]] = {
    "portfolio": {"func": db.get_portfolio, "keys": {"ticker", "sector", "min_profit_loss", "max_profit_loss"}},
    "trades": {"func": db.get_trades, "keys": {"ticker", "operation_type", "since", "until", "min_value"}},
    "customer_profile": {"func": db.get_customer_profile, "keys": set()},
    "real_estate": {"func": db.get_real_estate, "keys": {"property_type", "status", "location", "min_value", "max_value"}},
    "market_movements": {"func": db.get_market_movements, "keys": {"ticker", "min_change_percent", "direction", "since", "sector"}},
    "news": {"func": db.search_news, "keys": {"news_query", "top_k", "category", "ticker"}},
}


def _sanitize_date(value: Any) -> str | None:
    if not isinstance(value, str):
        return value
    m = _ISO_DATE_RE.match(value.strip())
    return m.group(1) if m else None


def _build_kwargs(source: str, planned_filters: dict) -> dict:
    allowed = _SOURCES[source]["keys"]
    kwargs = {}
    for k, v in planned_filters.items():
        if k not in allowed:
            continue
        if v is None or (isinstance(v, str) and v.strip().lower() == _SENTINEL):
            continue
        if k in _DATE_KEYS:
            v = _sanitize_date(v)
            if v is None:
                continue
        kwargs[k] = v
    if source == "news":
        kwargs["query"] = kwargs.pop("news_query", "") or ""
    return kwargs


def _execute_query(source: str, planned_filters: dict) -> dict:
    """Run one planned query against db.py. Never raises."""
    record: dict[str, Any] = {"source": source, "filters": planned_filters}
    if source not in _SOURCES:
        record["error"] = f"unknown source: {source}"
        record["results"] = None
        return record

    kwargs = _build_kwargs(source, planned_filters)
    record["call"] = {"function": _SOURCES[source]["func"].__name__, "kwargs": kwargs}

    if source == "news" and not kwargs.get("query"):
        record["error"] = "news query missing"
        record["results"] = None
        record["result_count"] = 0
        return record

    try:
        results = _SOURCES[source]["func"](**kwargs)
    except DataLayerError as e:
        record["error"] = str(e)
        record["results"] = None
        return record
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        record["results"] = None
        return record

    record["error"] = None
    if isinstance(results, list):
        record["result_count"] = len(results)
        record["results"] = results
    else:
        record["result_count"] = 1 if results else 0
        record["results"] = results
    return record


# ---------------------------------------------------------------------------
# WebSocket pipeline
# ---------------------------------------------------------------------------

DEFAULT_TEXT_FILE = "client_calls/call_7_two_way.txt"

# The mock data layer is anchored to late May 2025 (latest trade 2025-05-20,
# market movements 2025-05-26, news up to 2025-05-23). Pin the agent's "today"
# there so spoken relative dates ("today", "last couple of weeks") resolve INTO
# the data window instead of the real wall-clock date (which would return empty).
DEMO_NOW = date(2025, 5, 26)
UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Accept an MP3 upload, save it, return the path for the WS start message."""
    dest = UPLOADS_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)
    return {"path": str(dest), "filename": file.filename}


@app.websocket("/ws")
async def websocket_pipeline(ws: WebSocket):
    await ws.accept()
    try:
        # Wait for the start command
        raw = await ws.receive_text()
        msg = json.loads(raw)

        if msg.get("type") != "start":
            await ws.send_json({"type": "error", "message": "expected {type: 'start'}"})
            await ws.close()
            return

        file_path = msg.get("file", DEFAULT_TEXT_FILE)
        mode = msg.get("mode", "text")  # "text" or "audio"

        # Resolve relative paths against the speech-to-text directory
        resolved = Path(file_path)
        if not resolved.is_absolute():
            resolved = Path(__file__).parent / file_path

        if not resolved.is_file():
            await ws.send_json({"type": "error", "message": f"file not found: {resolved}"})
            await ws.close()
            return

        # Build callbacks that push messages over the WebSocket
        async def on_partial(text: str) -> None:
            try:
                await ws.send_json({"type": "partial", "text": text})
            except Exception:
                pass

        async def on_final(text: str, speaker: str = "client") -> None:
            try:
                await ws.send_json({"type": "final", "text": text, "speaker": speaker})
            except Exception:
                pass

        async def on_trigger(chunk: ConceptChunk) -> None:
            # Execute planned queries
            executed = []
            for req in chunk.data_requests:
                result = _execute_query(req.source, req.filters)
                executed.append(result)

            payload = {
                "type": "concept",
                "index": chunk.index,
                "topic": chunk.topic,
                "intent": chunk.intent,
                "entities": chunk.entities,
                "text": chunk.text,
                "data_requests": [
                    {"source": r.source, "rationale": r.rationale}
                    for r in chunk.data_requests
                ],
                "executed_queries": executed,
            }
            try:
                await ws.send_json(payload)
            except Exception:
                pass

        # Run the pipeline
        if mode == "audio":
            await run_file(
                str(resolved),
                on_trigger=on_trigger,
                on_partial=on_partial,
                on_final=on_final,
                realtime=True,
                now=DEMO_NOW,
            )
        else:
            # Text mode: read the script, stream utterances through segmenter
            text = resolved.read_text()
            await run_text(text, on_trigger=on_trigger, on_final=on_final, now=DEMO_NOW)

        await ws.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            await ws.send_json({"type": "error", "message": f"{type(e).__name__}: {e}"})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)

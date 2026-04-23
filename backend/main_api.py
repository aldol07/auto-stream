"""
FastAPI wrapper around the AutoStream LangGraph agent.

From project root:
  uvicorn backend.main_api:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from .agent import build_graph, get_initial_state

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
# Do not override env vars already set by the host (e.g. Render, Docker)
load_dotenv(ROOT / ".env", override=False)

LEADS_LOG_PATH = BACKEND / "leads_log.json"


def _cors_allowed_origins() -> list[str]:
    """Local dev + optional CORS_ORIGINS (comma‑separated) for Render or other frontends."""
    local = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]
    extra = os.getenv("CORS_ORIGINS", "").strip()
    if not extra:
        return local
    more = [o.strip() for o in extra.split(",") if o.strip()]
    # Preserve order, dedupe
    seen: set[str] = set()
    out: list[str] = []
    for o in local + more:
        if o not in seen:
            seen.add(o)
            out.append(o)
    return out


app = FastAPI(title="AutoStream Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_graph = None
_sessions: dict[str, dict] = {}


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _last_ai_content(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            return m.content or ""
    return ""


# ─── Schemas ─────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)


class LeadPayload(BaseModel):
    name: str | None
    email: str | None
    platform: str | None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    lead_captured: bool
    lead: LeadPayload


class ResetRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class HealthResponse(BaseModel):
    status: str
    model: str = "gemini-2.5-flash"
    gemini_key_configured: bool = False


def _gemini_key_present() -> bool:
    g = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    return bool(g.strip())


# ─── Routes ─────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    ok = _gemini_key_present()
    return HealthResponse(
        status="ok" if ok else "degraded",
        gemini_key_configured=ok,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = (req.session_id or "").strip() or str(uuid.uuid4())
    if session_id not in _sessions:
        _sessions[session_id] = get_initial_state()

    state = _sessions[session_id]
    state = {
        **state,
        "messages": state["messages"] + [HumanMessage(content=req.message.strip())],
    }

    try:
        result = get_graph().invoke(state)
    except Exception as e:
        msg = str(e)
        if len(msg) > 2000:
            msg = msg[:2000] + "…"
        raise HTTPException(status_code=500, detail=msg) from e

    _sessions[session_id] = result
    messages = result.get("messages", [])
    reply = _last_ai_content(messages)
    lead = LeadPayload(
        name=result.get("lead_name"),
        email=result.get("lead_email"),
        platform=result.get("lead_platform"),
    )
    return ChatResponse(
        session_id=session_id,
        reply=reply,
        intent=result.get("intent", "greeting"),
        lead_captured=bool(result.get("lead_captured")),
        lead=lead,
    )


@app.post("/reset")
def reset(req: ResetRequest):
    session_id = req.session_id.strip()
    if session_id in _sessions:
        del _sessions[session_id]
    return {"ok": True, "session_id": session_id}


@app.get("/leads")
def list_leads():
    if not LEADS_LOG_PATH.exists():
        return []
    try:
        with open(LEADS_LOG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


if __name__ == "__main__":
    import uvicorn

    os.chdir(ROOT)
    uvicorn.run("backend.main_api:app", host="0.0.0.0", port=8000, reload=True)

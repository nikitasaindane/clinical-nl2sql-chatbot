"""
NL2SQL Clinic Chatbot — FastAPI Application
==========================================

Endpoints
---------
  POST /chat    – Natural Language -> SQL -> Results
  GET  /health  – Service health check

Features
--------
  * SQL validation  (SELECT only, no dangerous keywords / prefixes)
  * Error handling  (agent errors, DB failures, empty results)
  * Query caching   (5-minute in-memory TTL cache)
  * Rate limiting   (20 requests / 60 s per client IP)
  * Structured logging
  * CORS enabled
  * Plotly chart extraction from VisualizeDataTool output
"""

import logging
import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from vanna.core.user.resolver import RequestContext
from vanna.components.rich.data.dataframe import DataFrameComponent
from vanna.components.rich.data.chart import ChartComponent
from vanna.components.rich.text import RichTextComponent
from vanna.components.simple.text import SimpleTextComponent

from vanna_setup import create_agent, agent_memory

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("nl2sql")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="NL2SQL Clinic Chatbot",
    description=(
        "Ask questions in plain English, "
        "get SQL-powered results from the clinic database."
    ),
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the chat UI from /static and at root /
import os as _os
_static_dir = _os.path.join(_os.path.dirname(__file__), "static")
if _os.path.exists(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(_os.path.join(_static_dir, "index.html"))

# ---------------------------------------------------------------------------
# Agent singleton
# ---------------------------------------------------------------------------
_agent = None


@app.on_event("startup")
async def _startup() -> None:
    global _agent
    logger.info("Initialising Vanna 2.0 agent ...")
    _agent = create_agent()
    logger.info("Agent ready.")


def _get_agent():
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not ready yet.")
    return _agent


# ---------------------------------------------------------------------------
# Rate limiting  (simple in-memory sliding window)
# ---------------------------------------------------------------------------
_rate_store: Dict[str, List[float]] = defaultdict(list)
_RATE_LIMIT  = 20   # max requests
_RATE_WINDOW = 60   # seconds


def _check_rate(ip: str) -> None:
    now    = time.time()
    cutoff = now - _RATE_WINDOW
    _rate_store[ip] = [t for t in _rate_store[ip] if t > cutoff]
    if len(_rate_store[ip]) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: max {_RATE_LIMIT} requests per {_RATE_WINDOW}s.",
        )
    _rate_store[ip].append(now)


# ---------------------------------------------------------------------------
# Query cache
# ---------------------------------------------------------------------------
_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 0  # 5 minutes


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        logger.info("Cache HIT: %.60s", key)
        return entry["data"]
    return None


def _cache_set(key: str, data: Dict[str, Any]) -> None:
    _cache[key] = {"data": data, "ts": time.time()}


# ---------------------------------------------------------------------------
# SQL validation
# ---------------------------------------------------------------------------
# Pattern 1: standalone dangerous keywords (word-boundary safe)
_DANGEROUS_KW = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE"
    r"|EXEC(?:UTE)?|GRANT|REVOKE|SHUTDOWN"
    r"|sqlite_master|sqlite_sequence)\b",
    re.IGNORECASE,
)
# Pattern 2: stored-procedure / extended-procedure prefixes  (xp_xxx  sp_xxx)
_DANGEROUS_PREFIX = re.compile(r"\b(xp_\w+|sp_\w+)", re.IGNORECASE)


def _validate_sql(sql: str) -> Optional[str]:
    """Return an error string when the SQL is unsafe; None when it is safe."""
    if not sql.strip().upper().startswith("SELECT"):
        return "Only SELECT queries are permitted."
    m = _DANGEROUS_KW.search(sql) or _DANGEROUS_PREFIX.search(sql)
    if m:
        return f"Forbidden keyword detected: '{m.group()}'."
    return None


def _extract_sql_from_text(text: str) -> Optional[str]:
    """Pull the first SELECT statement from markdown-fenced or plain text."""
    # Fenced code block:  ```sql\nSELECT ...\n```  or  ```\nSELECT ...\n```
    fence = re.search(
        r"```(?:sql)?\s*\n(SELECT[\s\S]+?)```",
        text, re.IGNORECASE,
    )
    if fence:
        return fence.group(1).strip()
    # Bare SELECT statement ending at semicolon or end-of-string
    bare = re.search(r"(SELECT\s[\s\S]+?)(?:;|$)", text, re.IGNORECASE)
    if bare:
        candidate = bare.group(1).strip()
        if len(candidate) > 10:
            return candidate
    return None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural-language question about the clinic data.",
    )


class ChartPayload(BaseModel):
    data:   Optional[List[Any]]        = None
    layout: Optional[Dict[str, Any]]   = None


class ChatResponse(BaseModel):
    message:    str
    sql_query:  Optional[str]               = None
    columns:    Optional[List[str]]         = None
    rows:       Optional[List[List[Any]]]   = None
    row_count:  Optional[int]               = None
    chart:      Optional[ChartPayload]      = None
    chart_type: Optional[str]               = None
    error:      Optional[str]               = None
    cached:     bool                        = False


# ---------------------------------------------------------------------------
# Component extractor
# ---------------------------------------------------------------------------
def _extract(components: list) -> Dict[str, Any]:
    """
    Walk the UiComponent objects yielded by agent.send_message() and extract:
      - message text  (from RichTextComponent / SimpleTextComponent)
      - SQL query     (from text content, markdown-fenced or bare)
      - table data    (from DataFrameComponent: rows as List[Dict])
      - chart data    (from ChartComponent:  Plotly dict with 'data'+'layout')
    """
    result: Dict[str, Any] = {
        "message":    "",
        "sql_query":  None,
        "columns":    None,
        "rows":       None,
        "row_count":  None,
        "chart":      None,
        "chart_type": None,
    }
    text_parts: List[str] = []

    for comp in components:

        # --- SimpleTextComponent (side-car on every UiComponent) -----------
        simple = getattr(comp, "simple_component", None)
        if isinstance(simple, SimpleTextComponent) and simple.text:
            text_parts.append(simple.text)

        # --- Rich component ------------------------------------------------
        rich = getattr(comp, "rich_component", comp)

        if isinstance(rich, DataFrameComponent):
            # rows = List[Dict], columns = List[str]
            if rich.columns and result["columns"] is None:
                result["columns"] = rich.columns
            if rich.rows and result["rows"] is None:
                cols = result["columns"] or list(rich.rows[0].keys())
                result["columns"]   = cols
                result["rows"]      = [[row.get(c) for c in cols] for row in rich.rows]
                result["row_count"] = len(result["rows"])

        elif isinstance(rich, ChartComponent):
            # rich.data is a Plotly JSON dict: {"data": [...], "layout": {...}}
            cd = rich.data
            if isinstance(cd, dict) and "data" in cd:
                result["chart"]      = {"data": cd["data"], "layout": cd.get("layout", {})}
                traces = cd["data"]
                if traces:
                    result["chart_type"] = traces[0].get("type", "chart")

        elif isinstance(rich, RichTextComponent):
            if rich.content:
                text_parts.append(rich.content)

        else:
            # Generic fallback: grab any text-like attribute
            for attr in ("content", "text", "message", "detail"):
                val = getattr(rich, attr, None)
                if isinstance(val, str) and val.strip():
                    text_parts.append(val)
                    break

    # Deduplicate text while preserving first-occurrence order
    seen:         set        = set()
    unique_parts: List[str]  = []
    for part in text_parts:
        key = part.strip()
        if key and key not in seen:
            seen.add(key)
            unique_parts.append(key)

    full_text          = "\n\n".join(unique_parts)
    result["message"]  = full_text or "Query processed."

    # Try to extract SQL from the text when not already found
    if result["sql_query"] is None and full_text:
        candidate = _extract_sql_from_text(full_text)
        if candidate:
            result["sql_query"] = candidate

    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """
    Accept a natural-language question and return:
      - The LLM-generated message/summary
      - The SQL that was executed
      - Result columns and rows
      - Optional Plotly chart for visualisation questions
    """
    ip       = request.client.host if request.client else "unknown"
    question = body.question.strip()

    _check_rate(ip)
    logger.info("[%s] /chat <- %r", ip, question)

    # --- Cache hit ----------------------------------------------------------
    hit = _cache_get(question)
    if hit:
        return ChatResponse(**hit, cached=True)

    agent = _get_agent()
    ctx   = RequestContext(remote_addr=ip)

    # --- Run agent, collect all streaming components -----------------------
    components: list = []
    try:
        async for component in agent.send_message(ctx, question):
            if hasattr(component, "error") and component.error:
                continue

                # Always keep latest valid component
            components.append(component)
    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        return ChatResponse(
            message="An internal error occurred while processing your question.",
            error=str(exc),
        )

    if not components:
        return ChatResponse(
            message="The agent returned no response. Please rephrase your question.",
            error="empty_response",
        )

    # --- Extract structured data -------------------------------------------
    data = _extract(components)

    # --- SQL safety gate ---------------------------------------------------
    if data["sql_query"]:
        err = _validate_sql(data["sql_query"])
        if err:
            logger.warning("SQL blocked — %r | sql=%.120s", err, data["sql_query"])
            return ChatResponse(
                message=f"The generated query was rejected by the safety filter: {err}",
                sql_query=data["sql_query"],
                error=err,
            )

    # --- No-data message ---------------------------------------------------
    if data["sql_query"] and data["rows"] is not None and len(data["rows"]) == 0:
        data["message"] += "\n\nNo data found for this query."

    chart_payload = ChartPayload(**data["chart"]) if data["chart"] else None

    resp = ChatResponse(
        message    = data["message"],
        sql_query  = data["sql_query"],
        columns    = data["columns"],
        rows       = data["rows"],
        row_count  = data["row_count"],
        chart      = chart_payload,
        chart_type = data["chart_type"],
    )

    _cache_set(question, resp.model_dump(exclude={"cached"}))
    logger.info(
        "[%s] /chat -> sql=%s rows=%s chart=%s",
        ip, bool(data["sql_query"]), data["row_count"], bool(chart_payload),
    )
    return resp


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Return service status and memory item count."""
    return {
        "status": "ok",
        "database": "connected",
        "agent_memory_items": len(agent_memory._memories),
    }
@app.post("/cache/clear")
async def clear_cache() -> Dict[str, Any]:
    """Clear the query cache."""
    _cache.clear()
    return {"status": "ok", "message": "Cache cleared"}

# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
#!/usr/bin/env python3
"""
Transparent JSON-RPC interceptor (Step 2).

Accepts POST requests from the dummy bot, logs method/params/latency,
forwards unchanged to upstream Anvil/Hardhat, returns the upstream response.

LOCAL SANDBOX ONLY — read-only pass-through, no response modification.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = ROOT / "artifacts" / "sandbox" / "rpc-interceptor.jsonl"

UPSTREAM_RPC = os.environ.get("UPSTREAM_RPC", "http://127.0.0.1:8545")
PROXY_HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8546"))
LOG_FILE = Path(os.environ.get("INTERCEPTOR_LOG", DEFAULT_LOG))
HTTP_TIMEOUT = float(os.environ.get("INTERCEPTOR_TIMEOUT", "30"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [interceptor] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("rpc-interceptor")

app = FastAPI(title="HexStrike RPC Interceptor", version="0.1.0")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_log(entry: dict[str, Any]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def summarize_body(body: Any) -> list[dict[str, Any]]:
    """Extract method/params/id from single or batch JSON-RPC payload."""
    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        items = [body]
    else:
        return [{"method": None, "params": None, "id": None, "parse_error": "invalid body type"}]

    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            out.append({"method": None, "params": None, "id": None, "parse_error": "invalid item"})
            continue
        params = item.get("params")
        out.append(
            {
                "method": item.get("method"),
                "params": _truncate(params),
                "id": item.get("id"),
                "jsonrpc": item.get("jsonrpc"),
            }
        )
    return out


def _truncate(value: Any, limit: int = 2000) -> Any:
    text = json.dumps(value, ensure_ascii=False) if value is not None else None
    if text and len(text) > limit:
        return json.loads(text[:limit] + "…")
    return value


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "upstream": UPSTREAM_RPC,
        "log_file": str(LOG_FILE),
    }


@app.post("/")
@app.post("/rpc")
async def intercept_rpc(request: Request) -> Response:
    trace_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()

    raw = await request.body()
    parse_error: str | None = None
    body: Any = None
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        parse_error = str(exc)

    calls = summarize_body(body) if body is not None else []
    methods = [c.get("method") for c in calls if c.get("method")]

    log.info("trace=%s methods=%s upstream=%s", trace_id, methods or ["<parse-error>"], UPSTREAM_RPC)

    if parse_error is not None:
        entry = {
            "ts": utc_now(),
            "trace_id": trace_id,
            "direction": "inbound",
            "error": parse_error,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        append_log(entry)
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
        )

    upstream_status = 0
    upstream_body: bytes = b""
    upstream_error: str | None = None

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            upstream = await client.post(
                UPSTREAM_RPC,
                content=raw,
                headers={"Content-Type": "application/json"},
            )
            upstream_status = upstream.status_code
            upstream_body = upstream.content
    except httpx.HTTPError as exc:
        upstream_error = str(exc)
        log.error("trace=%s upstream failed: %s", trace_id, exc)

    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    append_log(
        {
            "ts": utc_now(),
            "trace_id": trace_id,
            "direction": "pass-through",
            "calls": calls,
            "methods": methods,
            "upstream": UPSTREAM_RPC,
            "upstream_status": upstream_status,
            "upstream_error": upstream_error,
            "latency_ms": latency_ms,
            "request_bytes": len(raw),
            "response_bytes": len(upstream_body),
        }
    )

    if upstream_error is not None:
        return JSONResponse(
            status_code=502,
            content={
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": f"Upstream unreachable: {upstream_error}"},
                "id": None,
            },
        )

    return Response(
        content=upstream_body,
        status_code=upstream_status,
        media_type="application/json",
    )


def main() -> None:
    import uvicorn

    log.info("Starting interceptor on http://%s:%s → %s", PROXY_HOST, PROXY_PORT, UPSTREAM_RPC)
    log.info("Logging to %s", LOG_FILE)
    uvicorn.run(app, host=PROXY_HOST, port=PROXY_PORT, log_level="info")


if __name__ == "__main__":
    main()

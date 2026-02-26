from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib import error, request

from bot.config import settings


def _join_url(path: str) -> str:
    return f"{settings.BACKEND_API_BASE_URL.rstrip('/')}{path}"


def _http_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body: bytes | None = None
    headers = {"Content-Type": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(
        _join_url(path),
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


async def trigger_on_demand_scrape(filters: dict[str, Any], correlation_id: str) -> dict[str, Any]:
    payload = {
        "filters": filters,
        "correlation_id": correlation_id,
    }
    return await asyncio.to_thread(_http_json, "POST", "/api/scrape/trigger", payload)


async def get_scrape_status(job_id: str) -> dict[str, Any]:
    return await asyncio.to_thread(_http_json, "GET", f"/api/scrape/status/{job_id}")

from __future__ import annotations

from datetime import datetime
from threading import Lock, Semaphore, Thread
from typing import Any
from uuid import uuid4

from app.config import settings
from app.scraper.scraper import run_scraper

_ALLOWED_SIGNATURE_KEYS = (
    "brand",
    "model",
    "color",
    "min_price",
    "max_price",
    "min_year",
    "max_year",
)


class ScrapeJobManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._semaphore = Semaphore(max(1, settings.MAX_CONCURRENT_SCRAPES))
        self._jobs: dict[str, dict[str, Any]] = {}
        self._running_by_signature: dict[str, str] = {}

    def _build_signature(self, filters: dict[str, Any]) -> str:
        parts = []
        for key in _ALLOWED_SIGNATURE_KEYS:
            value = filters.get(key)
            if value is None:
                continue
            normalized = str(value).strip().lower()
            if not normalized:
                continue
            parts.append(f"{key}={normalized}")
        return "|".join(parts) or "global"

    def submit_job(
        self,
        *,
        filters: dict[str, Any],
        correlation_id: str,
    ) -> dict[str, Any]:
        signature = self._build_signature(filters)

        with self._lock:
            existing_job_id = self._running_by_signature.get(signature)
            if existing_job_id and existing_job_id in self._jobs:
                existing = self._jobs[existing_job_id]
                return {
                    "job_id": existing["job_id"],
                    "status": existing["status"],
                    "signature": existing["signature"],
                    "reused": True,
                }

            job_id = str(uuid4())
            now = datetime.utcnow().isoformat()
            job = {
                "job_id": job_id,
                "status": "pending",
                "signature": signature,
                "filters": filters,
                "correlation_id": correlation_id,
                "created_at": now,
                "started_at": None,
                "finished_at": None,
                "error": None,
                "result": {
                    "fetched": 0,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "expanded": 0,
                },
            }
            self._jobs[job_id] = job
            self._running_by_signature[signature] = job_id

        worker = Thread(target=self._run_job, args=(job_id,), daemon=True)
        worker.start()

        return {
            "job_id": job_id,
            "status": "pending",
            "signature": signature,
            "reused": False,
        }

    def _run_job(self, job_id: str) -> None:
        with self._semaphore:
            with self._lock:
                job = self._jobs.get(job_id)
                if not job:
                    return
                job["status"] = "running"
                job["started_at"] = datetime.utcnow().isoformat()
                filters = dict(job.get("filters") or {})

            try:
                page_limit = settings.SCRAPE_TARGET_MAX_PAGES if filters else settings.SCRAPE_MAX_PAGES
                result = run_scraper(
                    max_pages=page_limit,
                    target_filters=filters or None,
                    allow_fallback_expansion=True,
                )
                with self._lock:
                    job = self._jobs.get(job_id)
                    if not job:
                        return
                    job["status"] = "done"
                    job["result"] = result
                    job["finished_at"] = datetime.utcnow().isoformat()
            except Exception as exc:
                with self._lock:
                    job = self._jobs.get(job_id)
                    if not job:
                        return
                    job["status"] = "failed"
                    job["error"] = str(exc)
                    job["finished_at"] = datetime.utcnow().isoformat()
            finally:
                with self._lock:
                    job = self._jobs.get(job_id)
                    if job:
                        signature = job.get("signature")
                        if signature and self._running_by_signature.get(signature) == job_id:
                            self._running_by_signature.pop(signature, None)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return dict(job)


scrape_job_manager = ScrapeJobManager()

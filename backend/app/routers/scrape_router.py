from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.scraper.job_manager import scrape_job_manager

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


class ScrapeTriggerRequest(BaseModel):
    correlation_id: Optional[str] = None
    filters: dict[str, Any] = Field(default_factory=dict)


class ScrapeTriggerResponse(BaseModel):
    job_id: str
    status: str
    signature: str
    reused: bool


class ScrapeStatusResponse(BaseModel):
    job_id: str
    status: str
    signature: str
    correlation_id: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    result: dict[str, int]
    age_seconds: int


@router.post("/trigger", response_model=ScrapeTriggerResponse)
def trigger_scrape(payload: ScrapeTriggerRequest):
    correlation_id = payload.correlation_id or datetime.utcnow().strftime("req-%Y%m%d%H%M%S%f")
    result = scrape_job_manager.submit_job(
        filters=payload.filters,
        correlation_id=correlation_id,
    )
    return ScrapeTriggerResponse(**result)


@router.get("/status/{job_id}", response_model=ScrapeStatusResponse)
def get_scrape_status(job_id: str):
    job = scrape_job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scrape job not found")

    created_at = datetime.fromisoformat(job["created_at"])
    age_seconds = int((datetime.utcnow() - created_at).total_seconds())

    return ScrapeStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        signature=job["signature"],
        correlation_id=job["correlation_id"],
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        finished_at=job.get("finished_at"),
        error=job.get("error"),
        result=job.get("result") or {},
        age_seconds=max(age_seconds, 0),
    )

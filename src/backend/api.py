"""Local HTTP interface for already structured profile, JD and match data."""

from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Literal

from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.backend.storage import Store
from src.backend.validation import validate_match_references, validate_payload
from src.matching.scoring import score_match


DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "cv_assistant.sqlite3"
ApplicationStatus = Literal[
    "saved", "planned", "applied", "interview", "offer", "rejected", "withdrawn"
]


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    role: str = Field(min_length=1)
    job_id: str | None = None
    match_id: str | None = None
    applied_on: date | None = None
    status: ApplicationStatus = "saved"
    interviewed: bool = False
    notes: str = ""


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applied_on: date | None = None
    status: ApplicationStatus | None = None
    interviewed: bool | None = None
    notes: str | None = None


def _require_valid(kind: str, payload: dict[str, Any]) -> None:
    errors = validate_payload(kind, payload)
    if errors:
        raise HTTPException(status_code=422, detail=errors)


def create_app(db_path: Path | None = None) -> FastAPI:
    resolved_path = db_path or Path(os.environ.get("CV_ASSISTANT_DB_PATH", DEFAULT_DB))
    store = Store(resolved_path)
    app = FastAPI(title="AI 求职匹配助手 · 本地 API", version="0.1.0")
    app.state.store = store

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/profiles", status_code=201)
    def create_profile(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        _require_valid("profile", payload)
        try:
            return store.create_profile(payload)
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="Profile version already exists") from error

    @app.get("/profiles/{profile_version}")
    def get_profile(profile_version: str) -> dict[str, Any]:
        profile = store.get_profile(profile_version)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        return profile

    @app.post("/jobs", status_code=201)
    def create_job(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        _require_valid("job", payload)
        try:
            return store.create_job(payload)
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="Job ID already exists") from error

    @app.get("/jobs")
    def list_jobs() -> list[dict[str, Any]]:
        return store.list_jobs()

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        job = store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @app.post("/matches", status_code=201)
    def create_match(alignment: dict[str, Any] = Body(...)) -> dict[str, Any]:
        _require_valid("match", alignment)
        meta = alignment["match_meta"]
        profile = store.get_profile(meta["profile_version"])
        job = store.get_job(meta["job_id"])
        if profile is None or job is None:
            raise HTTPException(status_code=404, detail="Referenced profile or job not found")
        errors = validate_match_references(profile, job, alignment)
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        score = score_match(job, alignment)
        try:
            return store.create_match(alignment, score)
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="Match ID already exists") from error

    @app.get("/matches/{match_id}")
    def get_match(match_id: str) -> dict[str, Any]:
        match = store.get_match(match_id)
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")
        return match

    @app.post("/applications", status_code=201)
    def create_application(application: ApplicationCreate) -> dict[str, Any]:
        values = application.model_dump(mode="json")
        job_id = values["job_id"]
        match_id = values["match_id"]
        if job_id is not None and store.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail="Referenced job not found")
        if match_id is not None:
            match = store.get_match(match_id)
            if match is None:
                raise HTTPException(status_code=404, detail="Referenced match not found")
            if job_id is None or match["alignment"]["match_meta"]["job_id"] != job_id:
                raise HTTPException(status_code=422, detail="Match must belong to the selected job")
        return store.create_application(values)

    @app.get("/applications")
    def list_applications() -> list[dict[str, Any]]:
        return store.list_applications()

    @app.get("/applications/{application_id}")
    def get_application(application_id: str) -> dict[str, Any]:
        application = store.get_application(application_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Application not found")
        return application

    @app.patch("/applications/{application_id}")
    def update_application(application_id: str, update: ApplicationUpdate) -> dict[str, Any]:
        changes = update.model_dump(mode="json", exclude_unset=True)
        if "status" in changes and changes["status"] is None:
            raise HTTPException(status_code=422, detail="Status cannot be null")
        if "interviewed" in changes and changes["interviewed"] is None:
            raise HTTPException(status_code=422, detail="Interviewed cannot be null")
        if "notes" in changes and changes["notes"] is None:
            raise HTTPException(status_code=422, detail="Notes cannot be null")
        application = store.update_application(application_id, changes)
        if application is None:
            raise HTTPException(status_code=404, detail="Application not found")
        return application

    @app.delete("/applications/{application_id}", status_code=204)
    def delete_application(application_id: str) -> None:
        if not store.delete_application(application_id):
            raise HTTPException(status_code=404, detail="Application not found")

    return app


app = create_app()

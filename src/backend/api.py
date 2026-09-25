"""Local HTTP interface for already structured profile, JD and match data."""

from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Literal

from fastapi import Body, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from src.backend.storage import Store
from src.backend.validation import validate_match_references, validate_payload
from src.backend.job_parser import ParserFailure, ParserUnavailable, analyze_job_text
from src.backend.match_parser import analyze_match
from src.backend.profile_builder import analyze_profile
from src.backend.resume_rewriter import rewrite_resume_advice
from src.matching.scoring import score_match
from src.matching.resume_advice import build_resume_advice


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


class JobAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jd_text: str = Field(min_length=30, max_length=30000)
    source_type: Literal[
        "company_official", "school_channel", "recruiting_platform",
        "referral_repost", "unknown",
    ] = "unknown"
    source_reference: str = Field(default="user_paste", max_length=1000)


class MatchAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    consent_to_send_profile: bool = False


class ResumeRewriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_to_send_experience_facts: bool = False


class ProfileBasics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    school: str | None = None
    major: str | None = None
    degree: str | None = None
    graduation_year: int | None = None
    current_city: str | None = None


class ProfileAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_text: str = Field(min_length=20, max_length=30000)
    preferences_text: str = Field(min_length=20, max_length=10000)
    basic_info: ProfileBasics = Field(default_factory=ProfileBasics)
    consent_to_send_resume: bool = False


class ModelKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: SecretStr


def _require_valid(kind: str, payload: dict[str, Any]) -> None:
    errors = validate_payload(kind, payload)
    if errors:
        raise HTTPException(status_code=422, detail=errors)


def create_app(db_path: Path | None = None) -> FastAPI:
    resolved_path = db_path or Path(os.environ.get("CV_ASSISTANT_DB_PATH", DEFAULT_DB))
    store = Store(resolved_path)
    app = FastAPI(title="AI 求职匹配助手 · 本地 API", version="0.1.0")
    app.state.store = store
    app.state.deepseek_api_key = None

    def require_local(request: Request) -> None:
        if request.client is None or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            raise HTTPException(status_code=403, detail="Model key settings are local-only")

    def runtime_key() -> str | None:
        return app.state.deepseek_api_key

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/settings/model-status")
    def model_status() -> dict[str, Any]:
        provider = os.environ.get("CV_ASSISTANT_PROVIDER", "deepseek").lower()
        if provider == "deepseek":
            source = "runtime" if runtime_key() else "environment" if os.environ.get("DEEPSEEK_API_KEY") else "none"
        else:
            source = "environment" if os.environ.get("OPENAI_API_KEY") else "none"
        return {"provider": provider, "configured": source != "none", "source": source}

    @app.post("/settings/model-key")
    def set_model_key(payload: ModelKeyRequest, request: Request) -> dict[str, Any]:
        require_local(request)
        key = payload.api_key.get_secret_value().strip()
        if len(key) < 20:
            raise HTTPException(status_code=422, detail="API Key format is too short")
        app.state.deepseek_api_key = key
        return {"provider": "deepseek", "configured": True, "source": "runtime", "retention": "process_memory_only"}

    @app.delete("/settings/model-key")
    def clear_model_key(request: Request) -> dict[str, Any]:
        require_local(request)
        app.state.deepseek_api_key = None
        return model_status()

    @app.post("/profiles", status_code=201)
    def create_profile(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        _require_valid("profile", payload)
        try:
            return store.create_profile(payload)
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="Profile version already exists") from error

    @app.post("/profiles/analyze")
    def analyze_profile_draft(request: ProfileAnalyzeRequest) -> dict[str, Any]:
        if not request.consent_to_send_resume:
            raise HTTPException(
                status_code=422,
                detail="Confirm sending redacted resume and preference text to the model provider",
            )
        try:
            draft = analyze_profile(
                request.resume_text,
                request.preferences_text,
                request.basic_info.model_dump(),
                api_key=runtime_key(),
            )
        except ParserUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ParserFailure as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        if draft["profile_meta"]["input_status"] == "incompatible":
            raise HTTPException(status_code=422, detail="Input cannot form a job-seeker profile")
        return {"draft": draft, "saved": False}

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

    @app.post("/jobs/analyze")
    def analyze_job(request: JobAnalyzeRequest) -> dict[str, Any]:
        try:
            draft = analyze_job_text(
                request.jd_text, request.source_type, request.source_reference,
                api_key=runtime_key(),
            )
        except ParserUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ParserFailure as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        if draft["job_meta"]["input_status"] == "incompatible":
            raise HTTPException(status_code=422, detail="Input does not describe a job")
        return {"draft": draft, "saved": False}

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
        if profile["profile_meta"]["confirmation_status"] == "unconfirmed":
            raise HTTPException(status_code=422, detail="Confirm the profile before matching")
        errors = validate_match_references(profile, job, alignment)
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        score = score_match(job, alignment)
        try:
            return store.create_match(alignment, score)
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="Match ID already exists") from error

    @app.post("/matches/analyze")
    def analyze_match_draft(request: MatchAnalyzeRequest) -> dict[str, Any]:
        if not request.consent_to_send_profile:
            raise HTTPException(
                status_code=422,
                detail="Confirm sending the structured profile and job to the model provider",
            )
        profile = store.get_profile(request.profile_version)
        job = store.get_job(request.job_id)
        if profile is None or job is None:
            raise HTTPException(status_code=404, detail="Referenced profile or job not found")
        if profile["profile_meta"]["confirmation_status"] == "unconfirmed":
            raise HTTPException(status_code=422, detail="Confirm the profile before matching")
        try:
            alignment = analyze_match(profile, job, api_key=runtime_key())
        except ParserUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ParserFailure as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        return {
            "alignment": alignment,
            "score": score_match(job, alignment),
            "saved": False,
        }

    @app.get("/matches/{match_id}")
    def get_match(match_id: str) -> dict[str, Any]:
        match = store.get_match(match_id)
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")
        return match

    @app.get("/matches/{match_id}/resume-advice")
    def get_resume_advice(match_id: str) -> dict[str, Any]:
        match = store.get_match(match_id)
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")
        meta = match["alignment"]["match_meta"]
        profile = store.get_profile(meta["profile_version"])
        job = store.get_job(meta["job_id"])
        if profile is None or job is None:
            raise HTTPException(status_code=404, detail="Referenced profile or job not found")
        return build_resume_advice(profile, job, match["alignment"])

    @app.post("/matches/{match_id}/resume-rewrite")
    def analyze_resume_rewrite(match_id: str, request: ResumeRewriteRequest) -> dict[str, Any]:
        if not request.consent_to_send_experience_facts:
            raise HTTPException(status_code=422, detail="Confirm sending the selected experience facts to the model provider")
        match = store.get_match(match_id)
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")
        meta = match["alignment"]["match_meta"]
        profile = store.get_profile(meta["profile_version"])
        job = store.get_job(meta["job_id"])
        if profile is None or job is None:
            raise HTTPException(status_code=404, detail="Referenced profile or job not found")
        try:
            return rewrite_resume_advice(
                profile, job, match["alignment"], api_key=runtime_key()
            )
        except ParserUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ParserFailure as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

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

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobPostingRecord(SQLModel, table=True):
    __tablename__ = "job_postings"

    id: int | None = Field(default=None, primary_key=True)
    source: str
    url: str = Field(index=True, unique=True)
    title: str
    company: str | None = None
    location: str | None = None
    remote_type: str = "unknown"
    seniority: str = "unknown"
    contract_type: str = "unknown"
    description: str
    requirements_json: str = "[]"
    salary: str | None = None
    normalized_json: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class JobMatchRecord(SQLModel, table=True):
    __tablename__ = "job_matches"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job_postings.id", index=True)
    keyword: str
    score: float
    reasons_json: str
    missing_requirements_json: str
    risks_json: str = "[]"
    should_apply: bool = False
    requires_human_review: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class ApplicationAttemptRecord(SQLModel, table=True):
    __tablename__ = "application_attempts"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job_postings.id", index=True)
    status: str
    review_required: bool = True
    submitted_at: datetime | None = None
    result_json: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RunHistoryRecord(SQLModel, table=True):
    __tablename__ = "run_history"

    id: int | None = Field(default=None, primary_key=True)
    keyword: str
    source_count: int = 0
    jobs_found: int = 0
    matches_created: int = 0
    status: str = "completed"
    message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

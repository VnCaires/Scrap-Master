from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RemoteType(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class Seniority(StrEnum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    UNKNOWN = "unknown"


class ContractType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    UNKNOWN = "unknown"


class FieldInputType(StrEnum):
    TEXT = "text"
    EMAIL = "email"
    TEL = "tel"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    FILE = "file"
    UNKNOWN = "unknown"


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    SKIPPED = "skipped"
    SUBMITTED = "submitted"
    FAILED = "failed"


class Resume(BaseModel):
    pdf_path: Path
    summary: str | None = None
    extracted_text_path: Path | None = None

    @field_validator("pdf_path")
    @classmethod
    def must_be_pdf(cls, value: Path) -> Path:
        if value.suffix.lower() != ".pdf":
            raise ValueError("resume path must point to a PDF file")
        return value


class JobSource(BaseModel):
    name: str
    enabled: bool = True
    max_results: int = Field(default=20, ge=1)


class JobPosting(BaseModel):
    source: str
    url: str
    title: str
    company: str | None = None
    location: str | None = None
    remote_type: RemoteType = RemoteType.UNKNOWN
    seniority: Seniority = Seniority.UNKNOWN
    contract_type: ContractType = ContractType.UNKNOWN
    description: str
    requirements: list[str] = Field(default_factory=list)
    salary: str | None = None
    raw_html_path: Path | None = None
    created_at: datetime = Field(default_factory=utc_now)


class JobMatch(BaseModel):
    job: JobPosting
    keyword: str
    score: float = Field(ge=0.0, le=1.0)
    matched_reasons: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    should_apply: bool = False
    requires_human_review: bool = True


class FormField(BaseModel):
    field_id: str
    label: str
    html_name: str | None = None
    target_selector: str | None = None
    input_type: FieldInputType = FieldInputType.UNKNOWN
    mapped_profile_key: str | None = None
    proposed_value: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_human_review: bool = True
    reason: str = ""


class ApplicationForm(BaseModel):
    job: JobPosting
    fields: list[FormField] = Field(default_factory=list)
    submit_button_selector: str | None = None
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ApplicationDraft(BaseModel):
    job: JobPosting
    form: ApplicationForm | None = None
    status: ApplicationStatus = ApplicationStatus.NEEDS_REVIEW
    notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ApplicationResult(BaseModel):
    job: JobPosting
    status: ApplicationStatus
    submitted_at: datetime | None = None
    review_required: bool = True
    result_message: str | None = None
    errors: list[str] = Field(default_factory=list)

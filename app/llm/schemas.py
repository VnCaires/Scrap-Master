from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NormalizedJob(BaseModel):
    title: str
    company: str | None = None
    location: str | None = None
    remote_type: Literal["remote", "hybrid", "onsite", "unknown"] = "unknown"
    seniority: Literal["intern", "junior", "mid", "senior", "lead", "unknown"] = "unknown"
    contract_type: Literal[
        "full_time",
        "part_time",
        "contract",
        "internship",
        "temporary",
        "unknown",
    ] = "unknown"
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    salary: str | None = None
    language_requirements: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)


class CompatibilityEvaluation(BaseModel):
    keyword_similarity: float = Field(ge=0.0, le=1.0)
    skills_match: float = Field(ge=0.0, le=1.0)
    seniority_match: float = Field(ge=0.0, le=1.0)
    location_match: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)
    matched_reasons: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    should_apply: bool
    requires_human_review: bool = True

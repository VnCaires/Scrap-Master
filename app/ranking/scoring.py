from __future__ import annotations

import re

from app.config.settings import UserProfile
from app.core.models import JobMatch, JobPosting, RemoteType, Seniority
from app.llm.schemas import CompatibilityEvaluation


def rank_job(
    job: JobPosting,
    profile: UserProfile,
    keyword: str,
    llm_evaluation: CompatibilityEvaluation | None = None,
) -> JobMatch:
    keyword_score = _keyword_similarity(keyword, job)
    skills_score, missing_requirements = _skills_match(job.requirements, profile.experience.skills)
    seniority_score = _seniority_match(job.seniority, profile.experience.seniority)
    location_score = _location_match(job.remote_type, profile.preferences.remote_only)
    llm_score = llm_evaluation.overall_score if llm_evaluation else 0.5

    score = round(
        (0.30 * keyword_score)
        + (0.25 * skills_score)
        + (0.15 * seniority_score)
        + (0.10 * location_score)
        + (0.20 * llm_score),
        4,
    )

    reasons = _build_reasons(
        keyword_score=keyword_score,
        skills_score=skills_score,
        location_score=location_score,
        llm_evaluation=llm_evaluation,
    )
    risks = list(llm_evaluation.risks) if llm_evaluation else []
    if missing_requirements:
        risks.append("Some job requirements were not found in the profile skills.")

    return JobMatch(
        job=job,
        keyword=keyword,
        score=score,
        matched_reasons=reasons,
        missing_requirements=missing_requirements,
        risks=risks,
        should_apply=score >= 0.65 and not missing_requirements,
        requires_human_review=True,
    )


def rank_jobs(
    jobs: list[JobPosting],
    profile: UserProfile,
    keyword: str,
    llm_evaluations: dict[str, CompatibilityEvaluation] | None = None,
) -> list[JobMatch]:
    evaluations = llm_evaluations or {}
    matches = [
        rank_job(job, profile, keyword, evaluations.get(job.url))
        for job in jobs
    ]
    return sorted(matches, key=lambda match: match.score, reverse=True)


def _keyword_similarity(keyword: str, job: JobPosting) -> float:
    keyword_tokens = _tokens(keyword)
    if not keyword_tokens:
        return 0.0

    job_tokens = _tokens(" ".join([job.title, job.description, " ".join(job.requirements)]))
    overlap = keyword_tokens.intersection(job_tokens)
    return len(overlap) / len(keyword_tokens)


def _skills_match(requirements: list[str], skills: list[str]) -> tuple[float, list[str]]:
    if not requirements:
        return 0.5, []

    skill_tokens = {_normalize_text(skill) for skill in skills}
    missing = [
        requirement
        for requirement in requirements
        if _normalize_text(requirement) not in skill_tokens
    ]
    matched_count = len(requirements) - len(missing)
    return matched_count / len(requirements), missing


def _seniority_match(job_seniority: Seniority, profile_seniority: str | None) -> float:
    if job_seniority == Seniority.UNKNOWN or not profile_seniority:
        return 0.5
    return 1.0 if job_seniority.value == profile_seniority.lower() else 0.6


def _location_match(remote_type: RemoteType, remote_only: bool) -> float:
    if not remote_only:
        return 0.8
    if remote_type == RemoteType.REMOTE:
        return 1.0
    if remote_type == RemoteType.HYBRID:
        return 0.4
    if remote_type == RemoteType.ONSITE:
        return 0.0
    return 0.5


def _build_reasons(
    keyword_score: float,
    skills_score: float,
    location_score: float,
    llm_evaluation: CompatibilityEvaluation | None,
) -> list[str]:
    reasons: list[str] = []
    if keyword_score > 0:
        reasons.append("Job text overlaps with the requested keyword.")
    if skills_score >= 0.7:
        reasons.append("Profile skills cover most listed requirements.")
    if location_score >= 0.8:
        reasons.append("Location or remote policy matches preferences.")
    if llm_evaluation:
        reasons.extend(llm_evaluation.matched_reasons)
    if not reasons:
        reasons.append("Limited match signals were found; human review is required.")
    return reasons


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 1}


def _normalize_text(text: str) -> str:
    return " ".join(sorted(_tokens(text)))

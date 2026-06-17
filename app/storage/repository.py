from __future__ import annotations

import json

from sqlmodel import Session, select

from app.core.models import (
    ApplicationStatus,
    ContractType,
    JobMatch,
    JobPosting,
    RemoteType,
    Seniority,
)
from app.storage.models import (
    ApplicationAttemptRecord,
    JobMatchRecord,
    JobPostingRecord,
    RunHistoryRecord,
)


def save_job_postings(session: Session, jobs: list[JobPosting]) -> list[JobPostingRecord]:
    records: list[JobPostingRecord] = []
    for job in jobs:
        existing = session.exec(
            select(JobPostingRecord).where(JobPostingRecord.url == job.url)
        ).first()
        if existing:
            records.append(existing)
            continue

        record = JobPostingRecord(
            source=job.source,
            url=job.url,
            title=job.title,
            company=job.company,
            location=job.location,
            remote_type=job.remote_type.value,
            seniority=job.seniority.value,
            contract_type=job.contract_type.value,
            description=job.description,
            requirements_json=json.dumps(job.requirements),
            salary=job.salary,
        )
        session.add(record)
        session.flush()
        records.append(record)

    session.commit()
    return records


def list_job_postings(session: Session) -> list[JobPosting]:
    records = list_job_posting_records(session)
    return [job_from_record(record) for record in records]


def list_job_posting_records(session: Session) -> list[JobPostingRecord]:
    return list(session.exec(select(JobPostingRecord)).all())


def list_application_attempt_records(session: Session) -> list[ApplicationAttemptRecord]:
    statement = select(ApplicationAttemptRecord).order_by(ApplicationAttemptRecord.created_at.desc())
    return list(session.exec(statement).all())


def get_application_attempt_record(
    session: Session,
    attempt_id: int,
) -> ApplicationAttemptRecord | None:
    return session.get(ApplicationAttemptRecord, attempt_id)


def save_job_match(
    session: Session,
    job_record: JobPostingRecord,
    match: JobMatch,
) -> JobMatchRecord:
    if job_record.id is None:
        raise ValueError("job record must be persisted before saving a match")

    record = JobMatchRecord(
        job_id=job_record.id,
        keyword=match.keyword,
        score=match.score,
        reasons_json=json.dumps(match.matched_reasons),
        missing_requirements_json=json.dumps(match.missing_requirements),
        risks_json=json.dumps(match.risks),
        should_apply=match.should_apply,
        requires_human_review=match.requires_human_review,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def save_run_history(
    session: Session,
    keyword: str,
    source_count: int,
    jobs_found: int,
    matches_created: int,
    status: str = "completed",
    message: str | None = None,
) -> RunHistoryRecord:
    record = RunHistoryRecord(
        keyword=keyword,
        source_count=source_count,
        jobs_found=jobs_found,
        matches_created=matches_created,
        status=status,
        message=message,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def save_application_attempt(
    session: Session,
    job_record: JobPostingRecord,
    status: ApplicationStatus,
    review_required: bool,
    result: dict,
) -> ApplicationAttemptRecord:
    if job_record.id is None:
        raise ValueError("job record must be persisted before saving an application attempt")

    record = ApplicationAttemptRecord(
        job_id=job_record.id,
        status=status.value,
        review_required=review_required,
        submitted_at=None,
        result_json=json.dumps(result),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def job_from_record(record: JobPostingRecord) -> JobPosting:
    return JobPosting(
        source=record.source,
        url=record.url,
        title=record.title,
        company=record.company,
        location=record.location,
        remote_type=RemoteType(record.remote_type),
        seniority=Seniority(record.seniority),
        contract_type=ContractType(record.contract_type),
        description=record.description,
        requirements=json.loads(record.requirements_json),
        salary=record.salary,
    )

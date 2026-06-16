"""Persistence package."""

from app.storage.database import create_db_engine, init_database, session_scope
from app.storage.models import (
    ApplicationAttemptRecord,
    JobMatchRecord,
    JobPostingRecord,
    RunHistoryRecord,
)
from app.storage.repository import (
    job_from_record,
    list_job_posting_records,
    list_job_postings,
    save_job_match,
    save_job_postings,
    save_run_history,
)

__all__ = [
    "ApplicationAttemptRecord",
    "JobMatchRecord",
    "JobPostingRecord",
    "RunHistoryRecord",
    "create_db_engine",
    "init_database",
    "job_from_record",
    "list_job_posting_records",
    "list_job_postings",
    "save_job_match",
    "save_job_postings",
    "save_run_history",
    "session_scope",
]

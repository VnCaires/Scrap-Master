from app.sources import MockJobSource
from app.storage import (
    init_database,
    list_job_posting_records,
    save_job_postings,
    session_scope,
)


def test_save_job_postings_deduplicates_by_url(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'scrap_master.db'}"
    init_database(database_url)

    import asyncio

    jobs = asyncio.run(MockJobSource().search("Python", 2))
    with session_scope(database_url) as session:
        first = save_job_postings(session, jobs)
        second = save_job_postings(session, jobs)
        records = list_job_posting_records(session)

    assert len(first) == 2
    assert len(second) == 2
    assert len(records) == 2

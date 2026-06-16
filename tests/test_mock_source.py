import asyncio

from app.sources import MockJobSource


def test_mock_source_returns_jobs_with_limit() -> None:
    jobs = asyncio.run(MockJobSource().search(keyword="Python", limit=2))

    assert len(jobs) == 2
    assert all(job.source == "mock" for job in jobs)


def test_mock_source_falls_back_when_keyword_has_no_match() -> None:
    jobs = asyncio.run(MockJobSource().search(keyword="nonexistent-keyword", limit=1))

    assert len(jobs) == 1

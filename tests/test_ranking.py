from app.config.settings import load_profile
from app.ranking import rank_job
from app.sources import MockJobSource


def test_rank_job_explains_match(tmp_path) -> None:
    import asyncio

    profile = load_profile("config/profile.example.yaml")
    job = asyncio.run(MockJobSource().search("Python LLM", 1))[0]

    match = rank_job(job, profile, "Python LLM")

    assert match.score > 0.5
    assert match.requires_human_review is True
    assert match.matched_reasons


def test_rank_job_lists_missing_requirements() -> None:
    import asyncio

    profile = load_profile("config/profile.example.yaml")
    job = asyncio.run(MockJobSource().search("Python", 1))[0]
    profile.experience.skills = ["Python"]

    match = rank_job(job, profile, "Python")

    assert "LLM" in match.missing_requirements
    assert match.should_apply is False

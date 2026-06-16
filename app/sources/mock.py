from __future__ import annotations

from app.core.models import ContractType, JobPosting, RemoteType, Seniority
from app.sources.base import JobSourceAdapter


class MockJobSource(JobSourceAdapter):
    name = "mock"

    async def search(self, keyword: str, limit: int) -> list[JobPosting]:
        sample_jobs = [
            JobPosting(
                source=self.name,
                url="https://jobs.example.test/python-llm-engineer",
                title="Python LLM Engineer",
                company="Example AI Labs",
                location="Remote - Brazil",
                remote_type=RemoteType.REMOTE,
                seniority=Seniority.MID,
                contract_type=ContractType.FULL_TIME,
                description=(
                    "Build internal tools using Python, APIs, evaluation pipelines, "
                    "and LLM application patterns."
                ),
                requirements=["Python", "APIs", "LLM", "SQL"],
                salary=None,
            ),
            JobPosting(
                source=self.name,
                url="https://jobs.example.test/ml-automation-developer",
                title="Machine Learning Automation Developer",
                company="Workflow Systems",
                location="Hybrid - Sao Paulo",
                remote_type=RemoteType.HYBRID,
                seniority=Seniority.SENIOR,
                contract_type=ContractType.CONTRACT,
                description=(
                    "Automate data workflows and support model integration for "
                    "business operations."
                ),
                requirements=["Python", "Machine Learning", "Automation"],
                salary="BRL 12k-16k",
            ),
            JobPosting(
                source=self.name,
                url="https://jobs.example.test/backend-python",
                title="Backend Python Developer",
                company="Reliable Products",
                location="Remote",
                remote_type=RemoteType.REMOTE,
                seniority=Seniority.JUNIOR,
                contract_type=ContractType.FULL_TIME,
                description="Maintain backend services, APIs, tests, and data integrations.",
                requirements=["Python", "FastAPI", "SQL"],
                salary=None,
            ),
        ]

        lowered_keyword = keyword.strip().lower()
        if lowered_keyword:
            filtered = [
                job
                for job in sample_jobs
                if lowered_keyword in " ".join(
                    [job.title, job.description, " ".join(job.requirements)]
                ).lower()
            ]
        else:
            filtered = sample_jobs

        return (filtered or sample_jobs)[:limit]

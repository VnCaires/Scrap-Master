from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.models import JobPosting


class JobSourceAdapter(ABC):
    name: str

    @abstractmethod
    async def search(self, keyword: str, limit: int) -> list[JobPosting]:
        """Search jobs and return normalized core postings."""

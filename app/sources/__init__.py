"""Job source adapters."""

from app.sources.base import JobSourceAdapter
from app.sources.mock import MockJobSource

__all__ = ["JobSourceAdapter", "MockJobSource"]

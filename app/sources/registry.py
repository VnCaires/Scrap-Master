from __future__ import annotations

from app.config.settings import AppSettings
from app.core.models import JobSource
from app.sources.base import JobSourceAdapter
from app.sources.mock import MockJobSource


class UnknownJobSourceError(ValueError):
    """Raised when settings reference a source without an adapter."""


def get_source_adapter(source: JobSource) -> JobSourceAdapter:
    if source.name == "mock":
        return MockJobSource()
    raise UnknownJobSourceError(f"unsupported job source: {source.name}")


def get_enabled_source_adapters(settings: AppSettings) -> list[JobSourceAdapter]:
    return [get_source_adapter(source) for source in settings.enabled_sources()]

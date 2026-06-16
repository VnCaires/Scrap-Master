from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import Engine

import app.storage.models  # noqa: F401 - ensure SQLModel metadata knows all tables.


def create_db_engine(database_url: str, echo: bool = False) -> Engine:
    _ensure_sqlite_parent(database_url)
    return create_engine(database_url, echo=echo)


def init_database(database_url: str) -> None:
    engine = create_db_engine(database_url)
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope(database_url: str) -> Iterator[Session]:
    engine = create_db_engine(database_url)
    with Session(engine) as session:
        yield session


def _ensure_sqlite_parent(database_url: str) -> None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return

    path_text = database_url.removeprefix(prefix)
    if path_text in {":memory:", ""}:
        return

    Path(path_text).parent.mkdir(parents=True, exist_ok=True)

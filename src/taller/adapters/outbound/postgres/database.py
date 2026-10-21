from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from taller.adapters.outbound.postgres import tipos  # noqa: F401  (registra tipos por motor)


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy para todos los modelos ORM."""


def crear_engine(database_url: str) -> Engine:
    opciones: dict[str, Any] = {"pool_pre_ping": True, "future": True}
    if make_url(database_url).get_backend_name() == "mysql":
        # Mismo aislamiento que PostgreSQL por defecto; y MySQL corta conexiones
        # inactivas (wait_timeout), así que se reciclan antes.
        opciones |= {"isolation_level": "READ COMMITTED", "pool_recycle": 1800}
    return create_engine(database_url, **opciones)


def crear_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

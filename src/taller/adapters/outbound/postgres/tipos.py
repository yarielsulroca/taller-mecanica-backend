"""Tipos de columna que se comportan igual en PostgreSQL y en MySQL/MariaDB.

La app elige el motor por configuración (`TALLER_DB_MOTOR`); el dominio y los
casos de uso no se enteran. Lo propio de cada motor queda acá.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import functions
from sqlalchemy.sql.compiler import SQLCompiler, TypeCompiler
from sqlalchemy.types import TypeDecorator

# JSON: JSONB en PostgreSQL, JSON en MySQL.
JsonPortable = JSON().with_variant(JSONB(), "postgresql")

# Lista de textos (roles): arreglo nativo en PostgreSQL, JSON en MySQL.
ListaTexto = JSON().with_variant(ARRAY(String(20)), "postgresql")


class UtcDateTime(TypeDecorator[datetime]):
    """Fecha y hora siempre en UTC y *con* zona horaria al leer.

    PostgreSQL guarda la zona (timestamptz); MySQL no (DATETIME): se guarda la
    hora UTC sin zona y al leerla se le vuelve a poner UTC.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        if dialect.name == "postgresql":
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


@compiles(DateTime, "mysql")
def _datetime_mysql(tipo: DateTime, compiler: TypeCompiler, **kw: Any) -> str:
    # Microsegundos, como PostgreSQL (DATETIME a secas redondea al segundo).
    return "DATETIME(6)"


@compiles(functions.now, "mysql")
def _now_mysql(fn: functions.now, compiler: SQLCompiler, **kw: Any) -> str:
    # Debe coincidir con la precisión de DATETIME(6) en los DEFAULT.
    return "CURRENT_TIMESTAMP(6)"

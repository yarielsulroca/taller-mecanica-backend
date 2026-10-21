from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from taller.adapters.outbound.postgres import models  # noqa: F401  (registra tablas)
from taller.adapters.outbound.postgres.database import Base
from taller.config import get_settings

config = context.config
# configparser interpreta "%": se escapa por si la contraseña lo trae codificado.
config.set_main_option("sqlalchemy.url", get_settings().url_base_datos.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        comando = getattr(config.cmd_opts, "cmd", None)
        if connection.dialect.name == "mysql" and comando and comando[0].__name__ == "downgrade":
            # MySQL no deja borrar un índice que usa una FK aunque después se borre
            # la tabla; en la reversa se desactiva el chequeo (PostgreSQL no lo necesita).
            connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
            connection.commit()  # Alembic tiene que abrir (y confirmar) su propia transacción
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Configuración de la aplicación (12-factor: todo por entorno)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TALLER_",
        extra="ignore",
    )

    app_name: str = "Taller Mecánico API"
    environment: str = "dev"
    api_prefix: str = "/api/v1"

    # Base de datos: se elige el motor y la URL se arma sola. `database_url`
    # (TALLER_DATABASE_URL) es opcional y, si se define, tiene prioridad.
    db_motor: Literal["postgresql", "mysql"] = "postgresql"
    db_host: str = "localhost"
    db_puerto: int | None = None
    db_usuario: str = "taller"
    db_password: str = "taller"
    db_nombre: str = "taller"
    database_url: str | None = None

    jwt_secret: str = "dev-secret-change-me-please-32-bytes-min"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60

    # URL pública del frontend (HTTPS en prod). Se fusiona con cors_origins.
    frontend_url: str | None = None
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    storage_dir: str = "var/archivos"
    max_upload_mb: int = 50

    cumplimiento_activo: bool = True
    cumplimiento_minutos: int = 15
    comprobante_pendiente_dias: int = 3

    # Conexión opcional con ARCA: se activa desde Administración (por defecto, carga manual).
    arca_dir: str = "var/arca"
    arca_servicio_padron: str = "ws_sr_constancia_inscripcion"
    arca_timeout_seg: float = 15.0

    @model_validator(mode="after")
    def _ajustes_entorno(self) -> Settings:
        if self.frontend_url:
            base = self.frontend_url.rstrip("/")
            vistos: set[str] = set()
            unidos: list[str] = []
            for origen in (*self.cors_origins, base):
                o = origen.rstrip("/")
                if o not in vistos:
                    vistos.add(o)
                    unidos.append(o)
            self.cors_origins = unidos
        if self.environment == "prod" and (
            len(self.jwt_secret) < 32 or self.jwt_secret in _SECRETOS_DE_EJEMPLO
        ):
            raise ValueError("TALLER_JWT_SECRET debe ser propio y de 32+ caracteres en prod")
        return self

    @property
    def url_base_datos(self) -> str:
        if self.database_url:
            return self.database_url
        driver, puerto, query = _DRIVERS[self.db_motor]
        return URL.create(
            driver,
            username=self.db_usuario,
            password=self.db_password,
            host=self.db_host,
            port=self.db_puerto or puerto,
            database=self.db_nombre,
            query=query,
        ).render_as_string(hide_password=False)


_SECRETOS_DE_EJEMPLO = frozenset(
    {
        "dev-secret-change-me-please-32-bytes-min",
        "cambiar-este-secreto-por-uno-de-32-bytes-minimo",
    }
)

_DRIVERS: dict[str, tuple[str, int, dict[str, str]]] = {
    "postgresql": ("postgresql+psycopg", 5432, {}),
    "mysql": ("mysql+pymysql", 3306, {"charset": "utf8mb4"}),
}


@lru_cache
def get_settings() -> Settings:
    return Settings()

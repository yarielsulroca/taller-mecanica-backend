from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from taller.adapters.outbound.clock import SystemClock
from taller.adapters.outbound.ocr.adapter import OcrPypdfTesseract
from taller.adapters.outbound.postgres.database import crear_engine, crear_session_factory
from taller.adapters.outbound.realtime.bus import BusEnMemoria
from taller.adapters.outbound.security.password_hasher import Argon2PasswordHasher
from taller.adapters.outbound.security.token_service import JwtTokenService
from taller.adapters.outbound.storage.local import LocalArchivoStorage
from taller.config import Settings, get_settings


@dataclass
class Container:
    """Composition root: único lugar donde se instancian las implementaciones."""

    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    clock: SystemClock
    hasher: Argon2PasswordHasher
    tokens: JwtTokenService
    storage: LocalArchivoStorage
    ocr: OcrPypdfTesseract
    bus: BusEnMemoria


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    engine = crear_engine(settings.url_base_datos)
    return Container(
        settings=settings,
        engine=engine,
        session_factory=crear_session_factory(engine),
        clock=SystemClock(),
        hasher=Argon2PasswordHasher(),
        tokens=JwtTokenService(
            settings.jwt_secret,
            settings.jwt_algorithm,
            settings.access_token_minutes,
        ),
        storage=LocalArchivoStorage(Path(settings.storage_dir)),
        ocr=OcrPypdfTesseract(),
        bus=BusEnMemoria(),
    )

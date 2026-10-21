from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from taller.domain.entities.conexion_arca import ConexionArca
from taller.domain.enums import CondicionIva, TipoPersona


@dataclass(frozen=True, slots=True)
class DatosPadron:
    """Datos consultados al padrón (fuente externa).

    Son **sugerencias**: el operativo confirma o corrige antes de guardar
    (mismo principio que el OCR — RN-053: nunca inventar datos fiscales).
    """

    cuit: str
    fuente: str
    razon_social: str | None = None
    cond_iva: CondicionIva | None = None
    cond_iva_texto: str | None = None
    direccion: str | None = None
    tipo_persona: TipoPersona | None = None
    estado: str | None = None


class Padron(Protocol):
    def consultar(self, cuit: str) -> DatosPadron | None:
        """None si el CUIT no figura. Si el servicio falla: ServicioExternoNoDisponible."""
        ...


@dataclass(frozen=True, slots=True)
class CredencialesArca:
    certificado: bytes
    clave: bytes


@dataclass(frozen=True, slots=True)
class InfoCertificado:
    sujeto: str
    vence: date
    cuit: str | None


class BovedaArca(Protocol):
    """Guarda certificado y clave privada fuera de la base y del webroot."""

    def guardar(self, certificado: bytes, clave: bytes) -> InfoCertificado:
        """Valida que sean PEM y que la clave corresponda al certificado
        (ArchivoInvalido si no) y los persiste."""
        ...

    def leer(self) -> CredencialesArca | None: ...


FabricaPadronArca = Callable[[ConexionArca, CredencialesArca], Padron]


class ConexionArcaRepository(Protocol):
    def obtener(self) -> ConexionArca | None: ...
    def guardar(self, conexion: ConexionArca) -> None: ...

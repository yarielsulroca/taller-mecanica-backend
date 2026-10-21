"""Catálogo de excepciones de dominio.

Cada excepción lleva un ``code`` estable y un ``http_status``. El borde HTTP las
traduce con un único envelope de error (ver ``adapters/inbound/api/error_handlers``).
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    code: str = "error_dominio"
    http_status: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


# --- 400 / validación -------------------------------------------------------
class SolicitudInvalida(DomainError):
    code = "solicitud_invalida"
    http_status = 400


class PatenteInvalida(SolicitudInvalida):
    code = "patente_invalida"


class CuitInvalido(SolicitudInvalida):
    code = "cuit_invalido"


# --- 422 / validación de negocio -------------------------------------------
class ArchivoInvalido(DomainError):
    code = "archivo_invalido"
    http_status = 422


class IvaNoCuadra(DomainError):
    code = "iva_no_cuadra"
    http_status = 422


class KmInvalido(DomainError):
    code = "km_invalido"
    http_status = 422


# --- 401 / autenticación ----------------------------------------------------
class NoAutenticado(DomainError):
    code = "no_autenticado"
    http_status = 401


class CredencialesInvalidas(NoAutenticado):
    code = "credenciales_invalidas"


class TokenInvalido(NoAutenticado):
    code = "token_invalido"


# --- 403 / autorización -----------------------------------------------------
class SinPermiso(DomainError):
    code = "sin_permiso"
    http_status = 403


class UsuarioInactivo(SinPermiso):
    code = "usuario_inactivo"


# --- 404 --------------------------------------------------------------------
class NoEncontrado(DomainError):
    code = "no_encontrado"
    http_status = 404


# --- 409 / conflicto --------------------------------------------------------
class Conflicto(DomainError):
    code = "conflicto"
    http_status = 409


class Duplicado(Conflicto):
    code = "duplicado"


class ComprobanteNoEditable(Conflicto):
    code = "comprobante_no_editable"


class EstadoInvalido(Conflicto):
    code = "estado_invalido"


class OTCerrada(Conflicto):
    code = "ot_cerrada"


class PatenteDuplicada(Conflicto):
    code = "patente_duplicada"


class FacturaDuplicada(Conflicto):
    code = "factura_duplicada"


class CobroExcedeSaldo(Conflicto):
    code = "cobro_excede_saldo"


class SaldoPendiente(Conflicto):
    code = "saldo_pendiente"


class ConflictoConcurrencia(Conflicto):
    code = "conflicto_concurrencia"


class UltimoAdmin(Conflicto):
    code = "ultimo_admin"


# --- 502 / servicio externo -------------------------------------------------
class ServicioExternoNoDisponible(DomainError):
    code = "servicio_externo_no_disponible"
    http_status = 502

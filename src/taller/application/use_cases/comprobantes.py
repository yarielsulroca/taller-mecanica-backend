from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from taller.domain.entities.comprobante import Comprobante
from taller.domain.entities.configuracion import validar_tipo_comprobante
from taller.domain.enums import (
    ClasificacionComprobante,
    CondicionIva,
    CondicionPago,
    EstadoComprobante,
    OrigenComprobante,
    TipoComprobante,
)
from taller.domain.exceptions import FacturaDuplicada, NoEncontrado, SolicitudInvalida
from taller.domain.ports.configuracion import ConfiguracionTallerRepository
from taller.domain.ports.ocr import DatosComprobante, OcrComprobante
from taller.domain.ports.repositories import ComprobanteRepository


def _obtener(repo: ComprobanteRepository, comprobante_id: UUID) -> Comprobante:
    comprobante = repo.obtener(comprobante_id)
    if comprobante is None:
        raise NoEncontrado("Comprobante no encontrado")
    return comprobante


def _neto_por_defecto(cmd: RegistrarComprobanteCommand) -> Decimal:
    componentes = (
        cmd.iva21 + cmd.iva105 + cmd.iva27 + cmd.no_gravado + cmd.percep_iva + cmd.percep_iibb
    )
    if cmd.neto == 0 and componentes == 0:
        return cmd.total
    return cmd.neto


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrarComprobanteCommand:
    tipo: TipoComprobante
    clasificacion: ClasificacionComprobante
    fecha: date
    total: Decimal
    origen: OrigenComprobante = OrigenComprobante.TALLER
    emisor_cuit: str | None = None
    emisor_razon_social: str | None = None
    receptor_tipo: str | None = None
    receptor_id: UUID | None = None
    receptor_nombre: str | None = None
    pto_venta: int | None = None
    numero: int | None = None
    cae: str | None = None
    neto: Decimal = Decimal("0")
    iva21: Decimal = Decimal("0")
    iva105: Decimal = Decimal("0")
    iva27: Decimal = Decimal("0")
    no_gravado: Decimal = Decimal("0")
    percep_iva: Decimal = Decimal("0")
    percep_iibb: Decimal = Decimal("0")
    condicion: CondicionPago = CondicionPago.CONTADO
    archivo_path: str | None = None
    observaciones: str | None = None
    ot_ids: tuple[UUID, ...] = ()
    cond_iva_receptor: CondicionIva | None = None


def _construir(
    cmd: RegistrarComprobanteCommand, *, comprobante_id: UUID | None = None
) -> Comprobante:
    comprobante = Comprobante(
        tipo=cmd.tipo,
        clasificacion=cmd.clasificacion,
        origen=cmd.origen,
        fecha=cmd.fecha,
        total=cmd.total,
        emisor_cuit=cmd.emisor_cuit,
        emisor_razon_social=cmd.emisor_razon_social,
        receptor_tipo=cmd.receptor_tipo,
        receptor_id=cmd.receptor_id,
        receptor_nombre=cmd.receptor_nombre,
        pto_venta=cmd.pto_venta,
        numero=cmd.numero,
        cae=cmd.cae,
        neto=_neto_por_defecto(cmd),
        iva21=cmd.iva21,
        iva105=cmd.iva105,
        iva27=cmd.iva27,
        no_gravado=cmd.no_gravado,
        percep_iva=cmd.percep_iva,
        percep_iibb=cmd.percep_iibb,
        condicion=cmd.condicion,
        archivo_path=cmd.archivo_path,
        observaciones=cmd.observaciones,
        ot_ids=list(cmd.ot_ids),
    )
    if comprobante_id is not None:
        comprobante.id = comprobante_id
    return comprobante


class RegistrarComprobante:
    def __init__(
        self,
        repo: ComprobanteRepository,
        configuracion: ConfiguracionTallerRepository | None = None,
    ) -> None:
        self._repo = repo
        self._configuracion = configuracion

    def execute(self, cmd: RegistrarComprobanteCommand) -> Comprobante:
        comprobante = _construir(cmd)
        self._aplicar_reglas_fiscales(comprobante, cmd)
        if comprobante.es_fiscal:
            if (
                not comprobante.emisor_cuit
                or comprobante.pto_venta is None
                or comprobante.numero is None
            ):
                raise SolicitudInvalida(
                    "Un comprobante fiscal requiere CUIT emisor, punto de venta y número"
                )
            if self._repo.existe_fiscal(
                cuit_emisor=comprobante.emisor_cuit,
                tipo=comprobante.tipo.value,
                pto_venta=comprobante.pto_venta,
                numero=comprobante.numero,
            ):
                raise FacturaDuplicada(
                    "Ya existe un comprobante fiscal con ese CUIT, tipo, punto de venta y número",
                    details={
                        "cuit_emisor": comprobante.emisor_cuit,
                        "tipo": comprobante.tipo.value,
                        "pto_venta": comprobante.pto_venta,
                        "numero": comprobante.numero,
                    },
                )
        self._repo.guardar(comprobante)
        return comprobante

    def _aplicar_reglas_fiscales(
        self, comprobante: Comprobante, cmd: RegistrarComprobanteCommand
    ) -> None:
        """H1/H2: condición IVA del taller → tipo A/B/C, emisor y punto de venta."""
        if self._configuracion is None:
            return
        config = self._configuracion.obtener()
        if config is None:
            return
        if cmd.cond_iva_receptor is not None:
            validar_tipo_comprobante(config.cond_iva, cmd.cond_iva_receptor, cmd.tipo)
        config.validar_punto_venta(cmd.pto_venta)
        if cmd.clasificacion == ClasificacionComprobante.VENTA:
            if not comprobante.emisor_cuit:
                comprobante.emisor_cuit = str(config.cuit)
            if not comprobante.emisor_razon_social:
                comprobante.emisor_razon_social = config.razon_social


@dataclass(frozen=True, slots=True, kw_only=True)
class ActualizarComprobanteCommand(RegistrarComprobanteCommand):
    comprobante_id: UUID | None = None


class ActualizarComprobante:
    def __init__(
        self,
        repo: ComprobanteRepository,
        configuracion: ConfiguracionTallerRepository | None = None,
    ) -> None:
        self._repo = repo
        self._configuracion = configuracion

    def execute(self, cmd: ActualizarComprobanteCommand) -> Comprobante:
        if cmd.comprobante_id is None:
            raise SolicitudInvalida("Falta el identificador del comprobante")
        actual = _obtener(self._repo, cmd.comprobante_id)
        actual.exigir_editable()
        nuevo = _construir(cmd, comprobante_id=actual.id)
        if self._configuracion is not None and cmd.cond_iva_receptor is not None:
            config = self._configuracion.obtener()
            if config is not None:
                validar_tipo_comprobante(config.cond_iva, cmd.cond_iva_receptor, cmd.tipo)
        if nuevo.es_fiscal and self._repo.existe_fiscal(
            cuit_emisor=nuevo.emisor_cuit or "",
            tipo=nuevo.tipo.value,
            pto_venta=nuevo.pto_venta or 0,
            numero=nuevo.numero or 0,
        ):
            raise FacturaDuplicada("Ya existe un comprobante fiscal con esos datos")
        actual.tipo = nuevo.tipo
        actual.clasificacion = nuevo.clasificacion
        actual.fecha = nuevo.fecha
        actual.total = nuevo.total
        actual.emisor_cuit = nuevo.emisor_cuit
        actual.emisor_razon_social = nuevo.emisor_razon_social
        actual.receptor_tipo = nuevo.receptor_tipo
        actual.receptor_id = nuevo.receptor_id
        actual.receptor_nombre = nuevo.receptor_nombre
        actual.pto_venta = nuevo.pto_venta
        actual.numero = nuevo.numero
        actual.cae = nuevo.cae
        actual.neto = nuevo.neto
        actual.iva21 = nuevo.iva21
        actual.iva105 = nuevo.iva105
        actual.iva27 = nuevo.iva27
        actual.no_gravado = nuevo.no_gravado
        actual.percep_iva = nuevo.percep_iva
        actual.percep_iibb = nuevo.percep_iibb
        actual.condicion = nuevo.condicion
        actual.archivo_path = nuevo.archivo_path
        actual.observaciones = nuevo.observaciones
        actual.ot_ids = nuevo.ot_ids
        self._repo.guardar(actual)
        return actual


class ComprobarComprobante:
    def __init__(self, repo: ComprobanteRepository) -> None:
        self._repo = repo

    def execute(self, comprobante_id: UUID) -> Comprobante:
        comprobante = _obtener(self._repo, comprobante_id)
        comprobante.comprobar()
        self._repo.guardar(comprobante)
        return comprobante


class AnularComprobante:
    def __init__(self, repo: ComprobanteRepository) -> None:
        self._repo = repo

    def execute(self, comprobante_id: UUID) -> Comprobante:
        comprobante = _obtener(self._repo, comprobante_id)
        comprobante.anular()
        self._repo.guardar(comprobante)
        return comprobante


@dataclass(frozen=True, slots=True)
class ListarComprobantesQuery:
    clasificacion: ClasificacionComprobante | None = None
    estado: EstadoComprobante | None = None
    desde: date | None = None
    hasta: date | None = None
    q: str | None = None


class ListarComprobantes:
    def __init__(self, repo: ComprobanteRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarComprobantesQuery) -> list[Comprobante]:
        return self._repo.listar(
            clasificacion=query.clasificacion,
            estado=query.estado,
            desde=query.desde,
            hasta=query.hasta,
            q=query.q,
        )


class ObtenerComprobante:
    def __init__(self, repo: ComprobanteRepository) -> None:
        self._repo = repo

    def execute(self, comprobante_id: UUID) -> Comprobante:
        return _obtener(self._repo, comprobante_id)


class PreviewComprobante:
    """Devuelve los datos que el OCR pudo leer, para autocompletar el formulario (UC-061)."""

    def __init__(self, ocr: OcrComprobante) -> None:
        self._ocr = ocr

    def execute(self, *, contenido: bytes, content_type: str, nombre: str) -> DatosComprobante:
        return self._ocr.extraer(contenido=contenido, content_type=content_type, nombre=nombre)

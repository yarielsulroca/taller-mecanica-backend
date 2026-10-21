from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from taller.application.use_cases.efectivo import comprobar_efectivo
from taller.domain.entities.compra import Compra, CompraItem
from taller.domain.entities.comprobante import Comprobante
from taller.domain.entities.configuracion import validar_tipo_comprobante
from taller.domain.entities.movimiento import Cuota, Movimiento, Retencion, generar_cuotas
from taller.domain.entities.proveedor import Proveedor
from taller.domain.enums import (
    ClasificacionComprobante,
    CondicionPago,
    EstadoCompra,
    EstadoCuota,
    MedioPago,
    NaturalezaMovimiento,
    OrigenComprobante,
    OrigenCuota,
    Periodicidad,
    SignoMovimiento,
    TipoComprobante,
)
from taller.domain.exceptions import Conflicto, FacturaDuplicada, NoEncontrado, SolicitudInvalida
from taller.domain.ports.compras import CompraRepository
from taller.domain.ports.configuracion import ConfiguracionTallerRepository
from taller.domain.ports.finanzas import CuotaRepository, MovimientoRepository
from taller.domain.ports.repositories import ComprobanteRepository, ProveedorRepository


def _obtener(repo: CompraRepository, compra_id: UUID) -> Compra:
    compra = repo.obtener(compra_id)
    if compra is None:
        raise NoEncontrado("Compra no encontrada")
    return compra


@dataclass(frozen=True, slots=True)
class ItemCompraCommand:
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    alicuota_iva: Decimal = Decimal("0")
    rubro_id: UUID | None = None
    item_ot_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RegistrarCompraCommand:
    proveedor_id: UUID
    fecha: date
    items: tuple[ItemCompraCommand, ...]
    ot_id: UUID | None = None
    condicion_pago: CondicionPago = CondicionPago.CONTADO
    fecha_vencimiento: date | None = None
    comprobante_path: str | None = None
    observaciones: str | None = None
    plan_periodicidad: Periodicidad | None = None
    plan_cantidad: int | None = None
    tipo_comprobante: TipoComprobante | None = None
    pto_venta: int | None = None
    numero: int | None = None


class RegistrarCompra:
    def __init__(
        self,
        compras: CompraRepository,
        cuotas: CuotaRepository,
        proveedores: ProveedorRepository,
        comprobantes: ComprobanteRepository | None = None,
        configuracion: ConfiguracionTallerRepository | None = None,
    ) -> None:
        self._compras = compras
        self._cuotas = cuotas
        self._proveedores = proveedores
        self._comprobantes = comprobantes
        self._configuracion = configuracion

    def execute(self, cmd: RegistrarCompraCommand) -> Compra:
        if not cmd.items:
            raise SolicitudInvalida("La compra necesita al menos un ítem")
        proveedor = self._proveedores.obtener(cmd.proveedor_id)
        if proveedor is None:
            raise NoEncontrado("El proveedor indicado no existe")

        compra = Compra(
            proveedor_id=cmd.proveedor_id,
            fecha=cmd.fecha,
            ot_id=cmd.ot_id,
            condicion_pago=cmd.condicion_pago,
            fecha_vencimiento=cmd.fecha_vencimiento,
            comprobante_path=cmd.comprobante_path,
            observaciones=cmd.observaciones,
        )
        for item in cmd.items:
            compra.agregar_item(
                CompraItem(
                    descripcion=item.descripcion,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    alicuota_iva=item.alicuota_iva,
                    rubro_id=item.rubro_id,
                    item_ot_id=item.item_ot_id,
                )
            )

        # Toda compra genera al menos una cuota (a cuenta corriente puede tener plan).
        primer_vencimiento = cmd.fecha_vencimiento or cmd.fecha
        if cmd.condicion_pago == CondicionPago.CUENTA_CORRIENTE and cmd.fecha_vencimiento is None:
            raise SolicitudInvalida("Una compra a cuenta corriente requiere fecha de vencimiento")
        cantidad = cmd.plan_cantidad if cmd.plan_cantidad else 1
        periodicidad = cmd.plan_periodicidad or Periodicidad.UNICA
        cuotas = generar_cuotas(
            origen=OrigenCuota.PAGO,
            referencia_tipo="compra",
            referencia_id=compra.id,
            periodicidad=periodicidad,
            cantidad=cantidad,
            primer_vencimiento=primer_vencimiento,
            monto_total=compra.total,
            proveedor_id=compra.proveedor_id,
        )
        compra.tipo_comprobante = cmd.tipo_comprobante
        compra.pto_venta = cmd.pto_venta
        compra.numero = cmd.numero
        self._compras.guardar(compra)
        self._cuotas.guardar_muchas(cuotas)
        # H4: la compra con datos fiscales fluye a la tabla única de comprobantes.
        if cmd.tipo_comprobante is not None and self._comprobantes is not None:
            self._registrar_comprobante(compra, proveedor, cmd)
            self._compras.guardar(compra)
        return compra

    def _registrar_comprobante(
        self, compra: Compra, proveedor: Proveedor, cmd: RegistrarCompraCommand
    ) -> None:
        assert self._comprobantes is not None and cmd.tipo_comprobante is not None
        tipo = cmd.tipo_comprobante
        config = self._configuracion.obtener() if self._configuracion is not None else None
        if (
            tipo.value.startswith("factura")
            and config is not None
            and proveedor.cond_iva is not None
        ):
            # H2: el tipo lo definen el proveedor (emisor) y el taller (receptor).
            validar_tipo_comprobante(proveedor.cond_iva, config.cond_iva, tipo)
            if cmd.pto_venta is None or cmd.numero is None:
                raise SolicitudInvalida("Un comprobante fiscal requiere punto de venta y número")
            if self._comprobantes.existe_fiscal(
                cuit_emisor=str(proveedor.cuit),
                tipo=tipo.value,
                pto_venta=cmd.pto_venta,
                numero=cmd.numero,
            ):
                raise FacturaDuplicada(
                    "Ya existe un comprobante de compra con ese CUIT, tipo, punto de venta y número"
                )
        comprobante = Comprobante(
            tipo=tipo,
            clasificacion=ClasificacionComprobante.COMPRA,
            origen=OrigenComprobante.PROVEEDOR,
            fecha=compra.fecha,
            total=compra.total,
            emisor_cuit=str(proveedor.cuit),
            emisor_razon_social=proveedor.razon_social,
            receptor_tipo="taller",
            receptor_nombre=config.razon_social if config is not None else None,
            pto_venta=cmd.pto_venta,
            numero=cmd.numero,
            neto=compra.neto,
            iva21=compra.iva21,
            iva105=compra.iva105,
            iva27=compra.iva27,
            condicion=cmd.condicion_pago,
            archivo_path=cmd.comprobante_path,
            observaciones=cmd.observaciones,
            ot_ids=[compra.ot_id] if compra.ot_id is not None else [],
        )
        self._comprobantes.guardar(comprobante)
        compra.comprobante_id = comprobante.id


class AnularCompra:
    def __init__(self, compras: CompraRepository, cuotas: CuotaRepository) -> None:
        self._compras = compras
        self._cuotas = cuotas

    def execute(self, compra_id: UUID) -> Compra:
        compra = _obtener(self._compras, compra_id)
        compra.anular()
        for cuota in self._cuotas.listar(referencia_id=compra.id, origen=OrigenCuota.PAGO):
            cuota.estado = EstadoCuota.ANULADA
            self._cuotas.guardar(cuota)
        self._compras.guardar(compra)
        return compra


@dataclass(frozen=True, slots=True)
class ListarComprasQuery:
    proveedor_id: UUID | None = None
    ot_id: UUID | None = None
    estado: EstadoCompra | None = None
    desde: date | None = None
    hasta: date | None = None


class ListarCompras:
    def __init__(self, repo: CompraRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarComprasQuery) -> list[Compra]:
        return self._repo.listar(
            proveedor_id=query.proveedor_id,
            ot_id=query.ot_id,
            estado=query.estado,
            desde=query.desde,
            hasta=query.hasta,
        )


class ObtenerCompra:
    def __init__(self, repo: CompraRepository) -> None:
        self._repo = repo

    def execute(self, compra_id: UUID) -> Compra:
        return _obtener(self._repo, compra_id)


@dataclass(frozen=True, slots=True)
class RegistrarPagoCompraCommand:
    compra_id: UUID
    fecha: date
    monto: Decimal
    medio: MedioPago = MedioPago.EFECTIVO
    comprobante_id: UUID | None = None
    observaciones: str | None = None
    # H5/P3: retenciones que el taller aplica al pagar (SICORE/IIBB, certificado).
    retenciones: tuple[Retencion, ...] = ()
    # Id del egreso que se genera, para adjuntarle después el comprobante del pago.
    movimiento_id: UUID = field(default_factory=uuid4)


class RegistrarPagoCompra:
    """Paga (total o parcial) una compra, imputando a sus cuotas y generando el egreso."""

    def __init__(
        self,
        compras: CompraRepository,
        cuotas: CuotaRepository,
        movimientos: MovimientoRepository,
    ) -> None:
        self._compras = compras
        self._cuotas = cuotas
        self._movimientos = movimientos

    def execute(self, cmd: RegistrarPagoCompraCommand) -> Compra:
        compra = _obtener(self._compras, cmd.compra_id)
        if compra.estado == EstadoCompra.ANULADA:
            raise Conflicto("No se puede pagar una compra anulada")

        cuotas = sorted(
            self._cuotas.listar(referencia_id=compra.id, origen=OrigenCuota.PAGO),
            key=lambda c: c.numero,
        )
        saldo_total = sum((c.saldo for c in cuotas), Decimal("0.00"))
        total = cmd.monto + sum((r.monto for r in cmd.retenciones), Decimal("0.00"))
        if total > saldo_total:
            raise Conflicto("El pago (efectivo + retenciones) supera el saldo pendiente")

        restante = total
        for cuota in cuotas:
            if restante <= 0:
                break
            if cuota.saldo <= 0:
                continue
            aplicar = min(cuota.saldo, restante)
            cuota.registrar_pago(aplicar)
            self._cuotas.guardar(cuota)
            restante -= aplicar

        movimiento_pago = Movimiento(
            id=cmd.movimiento_id,
            fecha=cmd.fecha,
            signo=SignoMovimiento.EGRESO,
            naturaleza=NaturalezaMovimiento.PAGO_PROVEEDOR,
            monto=cmd.monto,  # caja: el efectivo entregado; retenciones aparte
            medio=cmd.medio,
            comprobante_id=cmd.comprobante_id,
            proveedor_id=compra.proveedor_id,
            ot_id=compra.ot_id,
            observaciones=cmd.observaciones,
            retenciones=list(cmd.retenciones),
        )
        comprobar_efectivo(movimiento_pago)
        self._movimientos.guardar(movimiento_pago)
        compra.estado = self._estado(cuotas)
        self._compras.guardar(compra)
        return compra

    @staticmethod
    def _estado(cuotas: list[Cuota]) -> EstadoCompra:
        if cuotas and all(c.estado == EstadoCuota.PAGADA for c in cuotas):
            return EstadoCompra.PAGADA
        if any(c.monto_pagado > 0 for c in cuotas):
            return EstadoCompra.PARCIAL
        return EstadoCompra.PENDIENTE

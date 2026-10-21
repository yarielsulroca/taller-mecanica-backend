from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from taller.application.use_cases.adjuntos_movimiento import (
    AdjuntarComprobante,
    AdjuntarComprobanteCommand,
    ListarAdjuntos,
    validar_adjunto,
)
from taller.application.use_cases.cobranza_ot import REFERENCIA_OT, CobranzaOT
from taller.application.use_cases.efectivo import comprobar_efectivo
from taller.domain.entities.movimiento import Movimiento, MovimientoAdjunto, Retencion
from taller.domain.enums import (
    MedioPago,
    NaturalezaMovimiento,
    RetencionTipo,
    SignoMovimiento,
)
from taller.domain.exceptions import NoEncontrado
from taller.domain.ports import Clock
from taller.domain.ports.finanzas import (
    CuotaRepository,
    MovimientoAdjuntoRepository,
    MovimientoRepository,
)
from taller.domain.ports.repositories import ClienteRepository
from taller.domain.ports.storage import ArchivoStorage

__all__ = ["AdjuntarComprobante", "AdjuntarComprobanteCommand", "ListarAdjuntos"]


@dataclass(frozen=True, slots=True)
class RetencionCommand:
    tipo: RetencionTipo
    monto: Decimal
    certificado: str | None = None


@dataclass(frozen=True, slots=True)
class RegistrarCobroCommand:
    cliente_id: UUID
    fecha: date
    monto: Decimal
    medio: MedioPago = MedioPago.EFECTIVO
    ot_id: UUID | None = None
    comprobante_id: UUID | None = None
    observaciones: str | None = None
    cuota_id: UUID | None = None
    adjunto_nombre: str | None = None
    adjunto_contenido: bytes | None = None
    adjunto_content_type: str | None = None
    adjunto_nota: str | None = None
    retenciones: tuple[RetencionCommand, ...] = ()


class RegistrarCobro:
    """Registra un cobro del cliente: movimiento ingreso, imputación opcional y adjunto."""

    def __init__(
        self,
        clientes: ClienteRepository,
        movimientos: MovimientoRepository,
        cuotas: CuotaRepository,
        adjuntos: MovimientoAdjuntoRepository,
        storage: ArchivoStorage,
        clock: Clock,
        cobranza: CobranzaOT | None = None,
    ) -> None:
        self._clientes = clientes
        self._movimientos = movimientos
        self._cuotas = cuotas
        self._adjuntos = adjuntos
        self._storage = storage
        self._clock = clock
        self._cobranza = cobranza

    def execute(self, cmd: RegistrarCobroCommand) -> Movimiento:
        if self._clientes.obtener(cmd.cliente_id) is None:
            raise NoEncontrado("El cliente indicado no existe")
        retenciones = [
            Retencion(tipo=r.tipo, monto=r.monto, certificado=r.certificado)
            for r in cmd.retenciones
        ]
        total_retenciones = sum((r.monto for r in retenciones), Decimal("0.00"))

        ot_id = cmd.ot_id
        cuota = None
        if cmd.cuota_id is not None:
            cuota = self._cuotas.obtener(cmd.cuota_id)
            if cuota is None:
                raise NoEncontrado("Cuota no encontrada")
            # H5: el cobro cubre el efectivo recibido + los certificados entregados.
            cuota.registrar_pago(cmd.monto + total_retenciones)
            if cuota.referencia_tipo == REFERENCIA_OT:
                ot_id = cuota.referencia_id
        elif ot_id is not None and self._cobranza is not None:
            self._cobranza.imputar(ot_id, cmd.monto + total_retenciones)

        movimiento = Movimiento(
            fecha=cmd.fecha,
            signo=SignoMovimiento.INGRESO,
            naturaleza=NaturalezaMovimiento.VENTA_TRABAJO,
            monto=cmd.monto,
            medio=cmd.medio,
            cliente_id=cmd.cliente_id,
            ot_id=ot_id,
            comprobante_id=cmd.comprobante_id,
            observaciones=cmd.observaciones,
            creado_en=self._clock.ahora(),
            retenciones=retenciones,
        )
        comprobar_efectivo(movimiento)
        self._movimientos.guardar(movimiento)
        if cuota is not None:
            self._cuotas.guardar(cuota)

        if cmd.adjunto_contenido is not None and cmd.adjunto_nombre:
            tipo = cmd.adjunto_content_type or ""
            validar_adjunto(cmd.adjunto_contenido, tipo)
            path = self._storage.guardar(
                nombre_original=cmd.adjunto_nombre,
                contenido=cmd.adjunto_contenido,
                content_type=tipo,
            )
            self._adjuntos.guardar(
                MovimientoAdjunto(
                    movimiento_id=movimiento.id,
                    archivo_path=path,
                    nombre_original=cmd.adjunto_nombre,
                    content_type=cmd.adjunto_content_type,
                    nota=cmd.adjunto_nota,
                    creado_en=self._clock.ahora(),
                )
            )
        if ot_id is not None and self._cobranza is not None:
            self._cobranza.cerrar_si_saldada(ot_id)
        return movimiento


class ListarCobros:
    """Cobros = movimientos de ingreso."""

    def __init__(self, movimientos: MovimientoRepository) -> None:
        self._movimientos = movimientos

    def execute(self, *, cliente_id: UUID | None = None) -> list[Movimiento]:
        return [
            m
            for m in self._movimientos.listar(signo=SignoMovimiento.INGRESO)
            if cliente_id is None or m.cliente_id == cliente_id
        ]

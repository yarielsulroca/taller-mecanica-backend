from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import (
    CuotaORM,
    MovimientoAdjuntoORM,
    MovimientoORM,
)
from taller.domain.entities.movimiento import Cuota, Movimiento, MovimientoAdjunto, Retencion
from taller.domain.enums import (
    EstadoCuota,
    EstadoMovimiento,
    MedioPago,
    NaturalezaMovimiento,
    OrigenCuota,
    RetencionTipo,
    SignoMovimiento,
)


def _movimiento(o: MovimientoORM) -> Movimiento:
    return Movimiento(
        id=o.id,
        fecha=o.fecha,
        signo=SignoMovimiento(o.signo),
        naturaleza=NaturalezaMovimiento(o.naturaleza),
        monto=o.monto,
        medio=MedioPago(o.medio),
        moneda=o.moneda,
        estado=EstadoMovimiento(o.estado),
        comprobante_id=o.comprobante_id,
        ot_id=o.ot_id,
        cliente_id=o.cliente_id,
        proveedor_id=o.proveedor_id,
        trabajador_id=o.trabajador_id,
        rubro_id=o.rubro_id,
        tipo_pago_id=o.tipo_pago_id,
        observaciones=o.observaciones,
        creado_en=o.creado_en,
        retenciones=[
            Retencion(
                tipo=RetencionTipo(str(r["tipo"])),
                monto=Decimal(str(r["monto"])),
                certificado=r.get("certificado"),
            )
            for r in (o.retenciones or [])
        ],
    )


def _cuota(o: CuotaORM) -> Cuota:
    return Cuota(
        id=o.id,
        origen=OrigenCuota(o.origen),
        referencia_tipo=o.referencia_tipo,
        referencia_id=o.referencia_id,
        numero=o.numero,
        fecha_vencimiento=o.fecha_vencimiento,
        monto=o.monto,
        monto_pagado=o.monto_pagado,
        estado=EstadoCuota(o.estado),
        cliente_id=o.cliente_id,
        proveedor_id=o.proveedor_id,
        notas=o.notas,
    )


class SqlMovimientoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, movimiento_id: UUID) -> Movimiento | None:
        orm = self._s.get(MovimientoORM, movimiento_id)
        return _movimiento(orm) if orm is not None else None

    def guardar(self, movimiento: Movimiento) -> None:
        orm = self._s.get(MovimientoORM, movimiento.id)
        if orm is None:
            orm = MovimientoORM(id=movimiento.id)
            self._s.add(orm)
        orm.fecha = movimiento.fecha
        orm.signo = movimiento.signo.value
        orm.naturaleza = movimiento.naturaleza.value
        orm.monto = movimiento.monto
        orm.medio = movimiento.medio.value
        orm.moneda = movimiento.moneda
        orm.estado = movimiento.estado.value
        orm.comprobante_id = movimiento.comprobante_id
        orm.ot_id = movimiento.ot_id
        orm.cliente_id = movimiento.cliente_id
        orm.proveedor_id = movimiento.proveedor_id
        orm.trabajador_id = movimiento.trabajador_id
        orm.rubro_id = movimiento.rubro_id
        orm.tipo_pago_id = movimiento.tipo_pago_id
        orm.observaciones = movimiento.observaciones
        orm.retenciones = [
            {
                "tipo": r.tipo.value,
                "monto": str(r.monto),
                "certificado": r.certificado,
            }
            for r in movimiento.retenciones
        ]
        orm.creado_en = movimiento.creado_en
        self._s.flush()

    def listar(
        self,
        *,
        signo: SignoMovimiento | None = None,
        naturaleza: NaturalezaMovimiento | None = None,
        estado: EstadoMovimiento | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        ot_id: UUID | None = None,
        proveedor_id: UUID | None = None,
        trabajador_id: UUID | None = None,
    ) -> list[Movimiento]:
        stmt = select(MovimientoORM)
        if signo is not None:
            stmt = stmt.where(MovimientoORM.signo == signo.value)
        if naturaleza is not None:
            stmt = stmt.where(MovimientoORM.naturaleza == naturaleza.value)
        if estado is not None:
            stmt = stmt.where(MovimientoORM.estado == estado.value)
        if desde is not None:
            stmt = stmt.where(MovimientoORM.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(MovimientoORM.fecha <= hasta)
        if ot_id is not None:
            stmt = stmt.where(MovimientoORM.ot_id == ot_id)
        if proveedor_id is not None:
            stmt = stmt.where(MovimientoORM.proveedor_id == proveedor_id)
        if trabajador_id is not None:
            stmt = stmt.where(MovimientoORM.trabajador_id == trabajador_id)
        filas = self._s.scalars(stmt.order_by(MovimientoORM.fecha.desc())).all()
        return [_movimiento(o) for o in filas]


class SqlCuotaRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, cuota_id: UUID) -> Cuota | None:
        orm = self._s.get(CuotaORM, cuota_id)
        return _cuota(orm) if orm is not None else None

    def _upsert(self, cuota: Cuota) -> None:
        orm = self._s.get(CuotaORM, cuota.id)
        if orm is None:
            orm = CuotaORM(id=cuota.id)
            self._s.add(orm)
        orm.origen = cuota.origen.value
        orm.referencia_tipo = cuota.referencia_tipo
        orm.referencia_id = cuota.referencia_id
        orm.numero = cuota.numero
        orm.fecha_vencimiento = cuota.fecha_vencimiento
        orm.monto = cuota.monto
        orm.monto_pagado = cuota.monto_pagado
        orm.estado = cuota.estado.value
        orm.cliente_id = cuota.cliente_id
        orm.proveedor_id = cuota.proveedor_id
        orm.notas = cuota.notas

    def guardar(self, cuota: Cuota) -> None:
        self._upsert(cuota)
        self._s.flush()

    def guardar_muchas(self, cuotas: list[Cuota]) -> None:
        for cuota in cuotas:
            self._upsert(cuota)
        self._s.flush()

    def listar(
        self,
        *,
        origen: OrigenCuota | None = None,
        referencia_id: UUID | None = None,
        estado: EstadoCuota | None = None,
    ) -> list[Cuota]:
        stmt = select(CuotaORM)
        if origen is not None:
            stmt = stmt.where(CuotaORM.origen == origen.value)
        if referencia_id is not None:
            stmt = stmt.where(CuotaORM.referencia_id == referencia_id)
        if estado is not None:
            stmt = stmt.where(CuotaORM.estado == estado.value)
        filas = self._s.scalars(stmt.order_by(CuotaORM.fecha_vencimiento)).all()
        return [_cuota(o) for o in filas]

    def listar_impagas(self) -> list[Cuota]:
        estados = (
            EstadoCuota.PENDIENTE.value,
            EstadoCuota.PARCIAL.value,
            EstadoCuota.VENCIDA.value,
        )
        stmt = select(CuotaORM).where(CuotaORM.estado.in_(estados))
        return [_cuota(o) for o in self._s.scalars(stmt)]

    def _saldo(self, columna: Any, valor: UUID, origen: OrigenCuota) -> Decimal:
        estados = (
            EstadoCuota.PENDIENTE.value,
            EstadoCuota.PARCIAL.value,
            EstadoCuota.VENCIDA.value,
        )
        total = self._s.scalar(
            select(func.coalesce(func.sum(CuotaORM.monto - CuotaORM.monto_pagado), 0)).where(
                columna == valor,
                CuotaORM.origen == origen.value,
                CuotaORM.estado.in_(estados),
            )
        )
        return Decimal(total or 0)

    def saldo_cliente(self, cliente_id: UUID) -> Decimal:
        return self._saldo(CuotaORM.cliente_id, cliente_id, OrigenCuota.COBRO)

    def saldo_proveedor(self, proveedor_id: UUID) -> Decimal:
        return self._saldo(CuotaORM.proveedor_id, proveedor_id, OrigenCuota.PAGO)

    def _saldos_por(self, columna: Any, origen: OrigenCuota) -> list[tuple[UUID, Decimal]]:
        estados = (
            EstadoCuota.PENDIENTE.value,
            EstadoCuota.PARCIAL.value,
            EstadoCuota.VENCIDA.value,
        )
        stmt = (
            select(columna, func.sum(CuotaORM.monto - CuotaORM.monto_pagado))
            .where(
                columna.isnot(None),
                CuotaORM.origen == origen.value,
                CuotaORM.estado.in_(estados),
            )
            .group_by(columna)
        )
        return [(fila[0], Decimal(fila[1] or 0)) for fila in self._s.execute(stmt)]

    def saldos_por_cliente(self) -> list[tuple[UUID, Decimal]]:
        return self._saldos_por(CuotaORM.cliente_id, OrigenCuota.COBRO)

    def saldos_por_proveedor(self) -> list[tuple[UUID, Decimal]]:
        return self._saldos_por(CuotaORM.proveedor_id, OrigenCuota.PAGO)


class SqlMovimientoAdjuntoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def guardar(self, adjunto: MovimientoAdjunto) -> None:
        self._s.add(
            MovimientoAdjuntoORM(
                id=adjunto.id,
                movimiento_id=adjunto.movimiento_id,
                archivo_path=adjunto.archivo_path,
                nombre_original=adjunto.nombre_original,
                content_type=adjunto.content_type,
                autor_id=adjunto.autor_id,
                nota=adjunto.nota,
                creado_en=adjunto.creado_en,
            )
        )
        self._s.flush()

    def listar(self, movimiento_id: UUID) -> list[MovimientoAdjunto]:
        stmt = (
            select(MovimientoAdjuntoORM)
            .where(MovimientoAdjuntoORM.movimiento_id == movimiento_id)
            .order_by(MovimientoAdjuntoORM.creado_en)
        )
        return [_adjunto(o) for o in self._s.scalars(stmt)]

    def obtener(self, adjunto_id: UUID) -> MovimientoAdjunto | None:
        orm = self._s.get(MovimientoAdjuntoORM, adjunto_id)
        return _adjunto(orm) if orm is not None else None

    def contar(self, movimiento_ids: Sequence[UUID]) -> dict[UUID, int]:
        if not movimiento_ids:
            return {}
        stmt = (
            select(MovimientoAdjuntoORM.movimiento_id, func.count())
            .where(MovimientoAdjuntoORM.movimiento_id.in_(movimiento_ids))
            .group_by(MovimientoAdjuntoORM.movimiento_id)
        )
        return {mid: int(n) for mid, n in self._s.execute(stmt)}


def _adjunto(o: MovimientoAdjuntoORM) -> MovimientoAdjunto:
    return MovimientoAdjunto(
        id=o.id,
        movimiento_id=o.movimiento_id,
        archivo_path=o.archivo_path,
        nombre_original=o.nombre_original,
        content_type=o.content_type,
        autor_id=o.autor_id,
        nota=o.nota,
        creado_en=o.creado_en,
    )

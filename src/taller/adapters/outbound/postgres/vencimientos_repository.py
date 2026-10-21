from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import GastoFijoORM, ObligacionORM
from taller.domain.entities.vencimiento import GastoFijo, Obligacion
from taller.domain.enums import EstadoObligacion, MedioPago, OrigenObligacion, PeriodicidadGasto


def _gasto(o: GastoFijoORM) -> GastoFijo:
    return GastoFijo(
        id=o.id,
        archivado_en=o.archivado_en,
        concepto=o.concepto,
        rubro_id=o.rubro_id,
        monto_estimado=o.monto_estimado,
        periodicidad=PeriodicidadGasto(o.periodicidad),
        dia_vencimiento=o.dia_vencimiento,
        fecha_inicio=o.fecha_inicio,
        fecha_fin=o.fecha_fin,
        dias_aviso=o.dias_aviso,
        medio=MedioPago(o.medio) if o.medio else None,
    )


def _obligacion(o: ObligacionORM) -> Obligacion:
    return Obligacion(
        id=o.id,
        origen=OrigenObligacion(o.origen),
        referencia_id=o.referencia_id,
        concepto=o.concepto,
        fecha_vencimiento=o.fecha_vencimiento,
        periodo_desde=o.periodo_desde,
        periodo_hasta=o.periodo_hasta,
        monto_estimado=o.monto_estimado,
        rubro_id=o.rubro_id,
        estado=EstadoObligacion(o.estado),
        movimiento_id=o.movimiento_id,
        liquidacion_id=o.liquidacion_id,
        motivo_omision=o.motivo_omision,
        resuelta_en=o.resuelta_en,
    )


class SqlGastoFijoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, gasto_id: UUID) -> GastoFijo | None:
        orm = self._s.get(GastoFijoORM, gasto_id)
        return _gasto(orm) if orm is not None else None

    def guardar(self, gasto: GastoFijo) -> None:
        orm = self._s.get(GastoFijoORM, gasto.id)
        if orm is None:
            orm = GastoFijoORM(id=gasto.id)
            self._s.add(orm)
        orm.archivado_en = gasto.archivado_en
        orm.concepto = gasto.concepto
        orm.rubro_id = gasto.rubro_id
        orm.monto_estimado = gasto.monto_estimado
        orm.periodicidad = gasto.periodicidad.value
        orm.dia_vencimiento = gasto.dia_vencimiento
        orm.fecha_inicio = gasto.fecha_inicio
        orm.fecha_fin = gasto.fecha_fin
        orm.dias_aviso = gasto.dias_aviso
        orm.medio = gasto.medio.value if gasto.medio else None
        self._s.flush()

    def listar(self, *, incluir_archivados: bool = False) -> list[GastoFijo]:
        stmt = select(GastoFijoORM)
        if not incluir_archivados:
            stmt = stmt.where(GastoFijoORM.archivado_en.is_(None))
        return [_gasto(o) for o in self._s.scalars(stmt.order_by(GastoFijoORM.concepto)).all()]


class SqlObligacionRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, obligacion_id: UUID) -> Obligacion | None:
        orm = self._s.get(ObligacionORM, obligacion_id)
        return _obligacion(orm) if orm is not None else None

    def guardar(self, obligacion: Obligacion) -> None:
        orm = self._s.get(ObligacionORM, obligacion.id)
        if orm is None:
            orm = ObligacionORM(id=obligacion.id)
            self._s.add(orm)
        orm.origen = obligacion.origen.value
        orm.referencia_id = obligacion.referencia_id
        orm.concepto = obligacion.concepto
        orm.fecha_vencimiento = obligacion.fecha_vencimiento
        orm.periodo_desde = obligacion.periodo_desde
        orm.periodo_hasta = obligacion.periodo_hasta
        orm.monto_estimado = obligacion.monto_estimado
        orm.rubro_id = obligacion.rubro_id
        orm.estado = obligacion.estado.value
        orm.movimiento_id = obligacion.movimiento_id
        orm.liquidacion_id = obligacion.liquidacion_id
        orm.motivo_omision = obligacion.motivo_omision
        orm.resuelta_en = obligacion.resuelta_en
        self._s.flush()

    def existe(
        self, *, origen: OrigenObligacion, referencia_id: UUID, fecha_vencimiento: date
    ) -> bool:
        stmt = select(ObligacionORM.id).where(
            ObligacionORM.origen == origen.value,
            ObligacionORM.referencia_id == referencia_id,
            ObligacionORM.fecha_vencimiento == fecha_vencimiento,
        )
        return self._s.scalar(stmt) is not None

    def listar(
        self,
        *,
        estado: EstadoObligacion | None = None,
        origen: OrigenObligacion | None = None,
        referencia_id: UUID | None = None,
    ) -> list[Obligacion]:
        stmt = select(ObligacionORM)
        if estado is not None:
            stmt = stmt.where(ObligacionORM.estado == estado.value)
        if origen is not None:
            stmt = stmt.where(ObligacionORM.origen == origen.value)
        if referencia_id is not None:
            stmt = stmt.where(ObligacionORM.referencia_id == referencia_id)
        stmt = stmt.order_by(ObligacionORM.fecha_vencimiento.desc()).limit(500)
        return [_obligacion(o) for o in self._s.scalars(stmt).all()]

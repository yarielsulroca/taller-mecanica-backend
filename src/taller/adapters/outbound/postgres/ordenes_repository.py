from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import (
    EvidenciaORM,
    ItemOTORM,
    OrdenTrabajoORM,
    ParticipacionORM,
    VehiculoORM,
)
from taller.domain.entities.orden_trabajo import Evidencia, ItemOT, OrdenTrabajo, Participacion
from taller.domain.enums import (
    EstadoItem,
    EstadoOT,
    MomentoEvidencia,
    OrigenPieza,
    Prioridad,
    TipoEvidencia,
    TipoItem,
)


def _item_dominio(o: ItemOTORM) -> ItemOT:
    return ItemOT(
        id=o.id,
        descripcion=o.descripcion,
        tipo=TipoItem(o.tipo),
        cantidad=o.cantidad,
        precio_unitario=o.precio_unitario,
        descuento=o.descuento,
        costo_unitario=o.costo_unitario,
        estado=EstadoItem(o.estado),
        origen_pieza=OrigenPieza(o.origen_pieza) if o.origen_pieza else None,
        mecanico_id=o.mecanico_id,
        notas=o.notas,
        motivo_no_realizado=o.motivo_no_realizado,
    )


def _participacion_dominio(o: ParticipacionORM) -> Participacion:
    return Participacion(
        id=o.id,
        mecanico_id=o.mecanico_id,
        desde=o.desde,
        hasta=o.hasta,
        horas=o.horas,
        notas=o.notas,
    )


def _evidencia_dominio(o: EvidenciaORM) -> Evidencia:
    return Evidencia(
        id=o.id,
        tipo=TipoEvidencia(o.tipo),
        momento=MomentoEvidencia(o.momento),
        archivo_path=o.archivo_path,
        nombre_original=o.nombre_original,
        autor_id=o.autor_id,
        item_id=o.item_id,
        nota=o.nota,
        creada_en=o.creada_en,
        content_type=o.content_type,
    )


def _patentes(session: Session, ids: set) -> dict:
    """Patente por vehículo (una sola consulta; del modelo maestro)."""
    vivos = [i for i in ids if i is not None]
    if not vivos:
        return {}
    filas = session.execute(
        select(VehiculoORM.id, VehiculoORM.patente).where(VehiculoORM.id.in_(vivos))
    ).all()
    return {id_: (patente or None) for id_, patente in filas}


def _a_dominio(o: OrdenTrabajoORM, patente: str | None = None) -> OrdenTrabajo:
    return OrdenTrabajo(
        id=o.id,
        numero=o.numero,
        vehiculo_id=o.vehiculo_id,
        cliente_id=o.cliente_id,
        empresa_id=o.empresa_id,
        patente=patente,
        estado=EstadoOT(o.estado),
        prioridad=Prioridad(o.prioridad),
        fecha_ingreso=o.fecha_ingreso,
        fecha_estimada=o.fecha_estimada,
        fecha_cierre=o.fecha_cierre,
        presupuesto_vigente_hasta=o.presupuesto_vigente_hasta,
        km_ingreso=o.km_ingreso,
        motivo_ingreso=o.motivo_ingreso,
        diagnostico=o.diagnostico,
        observaciones=o.observaciones,
        aprobado_por=o.aprobado_por,
        aprobado_canal=o.aprobado_canal,
        aprobado_en=o.aprobado_en,
        validado_por=o.validado_por,
        validado_en=o.validado_en,
        validado_nota=o.validado_nota,
        items=[_item_dominio(i) for i in o.items],
        participaciones=[_participacion_dominio(p) for p in o.participaciones],
        evidencias=[_evidencia_dominio(e) for e in o.evidencias],
        version=o.version,
    )


def _sincronizar(
    existentes: list[Any],
    deseados: list[Any],
    orm_cls: type,
    ot_id: UUID,
    mapear: Callable[[Any, Any], None],
) -> None:
    por_id = {c.id: c for c in existentes}
    deseados_ids = {d.id for d in deseados}
    for cid in [c.id for c in existentes]:
        if cid not in deseados_ids:
            existentes.remove(por_id[cid])
    for d in deseados:
        c = por_id.get(d.id)
        if c is None:
            c = orm_cls(id=d.id, ot_id=ot_id)
            existentes.append(c)
        mapear(d, c)


def _item_orm(d: ItemOT, c: ItemOTORM) -> None:
    c.descripcion = d.descripcion
    c.tipo = d.tipo.value
    c.cantidad = d.cantidad
    c.precio_unitario = d.precio_unitario
    c.descuento = d.descuento
    c.costo_unitario = d.costo_unitario
    c.estado = d.estado.value
    c.origen_pieza = d.origen_pieza.value if d.origen_pieza else None
    c.mecanico_id = d.mecanico_id
    c.notas = d.notas
    c.motivo_no_realizado = d.motivo_no_realizado


def _participacion_orm(d: Participacion, c: ParticipacionORM) -> None:
    c.mecanico_id = d.mecanico_id
    c.desde = d.desde
    c.hasta = d.hasta
    c.horas = d.horas
    c.notas = d.notas


def _evidencia_orm(d: Evidencia, c: EvidenciaORM) -> None:
    c.item_id = d.item_id
    c.tipo = d.tipo.value
    c.momento = d.momento.value
    c.archivo_path = d.archivo_path
    c.nombre_original = d.nombre_original
    c.content_type = d.content_type
    c.autor_id = d.autor_id
    c.nota = d.nota
    c.creada_en = d.creada_en


class SqlOrdenTrabajoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, ot_id: UUID) -> OrdenTrabajo | None:
        orm = self._s.get(OrdenTrabajoORM, ot_id)
        if orm is None:
            return None
        patente = _patentes(self._s, {orm.vehiculo_id}).get(orm.vehiculo_id)
        return _a_dominio(orm, patente)

    def siguiente_numero(self) -> int:
        ultimo = self._s.scalar(select(func.max(OrdenTrabajoORM.numero)))
        return int(ultimo or 0) + 1

    def guardar(self, ot: OrdenTrabajo) -> None:
        orm = self._s.get(OrdenTrabajoORM, ot.id)
        if orm is None:
            orm = OrdenTrabajoORM(id=ot.id)
            self._s.add(orm)
        orm.numero = ot.numero
        orm.vehiculo_id = ot.vehiculo_id
        orm.cliente_id = ot.cliente_id
        orm.empresa_id = ot.empresa_id
        orm.estado = ot.estado.value
        orm.prioridad = ot.prioridad.value
        orm.fecha_ingreso = ot.fecha_ingreso
        orm.fecha_estimada = ot.fecha_estimada
        orm.fecha_cierre = ot.fecha_cierre
        orm.presupuesto_vigente_hasta = ot.presupuesto_vigente_hasta
        orm.km_ingreso = ot.km_ingreso
        orm.motivo_ingreso = ot.motivo_ingreso
        orm.diagnostico = ot.diagnostico
        orm.observaciones = ot.observaciones
        orm.aprobado_por = ot.aprobado_por
        orm.aprobado_canal = ot.aprobado_canal
        orm.aprobado_en = ot.aprobado_en
        orm.validado_por = ot.validado_por
        orm.validado_en = ot.validado_en
        orm.validado_nota = ot.validado_nota
        orm.version = ot.version

        _sincronizar(orm.items, ot.items, ItemOTORM, ot.id, _item_orm)
        _sincronizar(
            orm.participaciones, ot.participaciones, ParticipacionORM, ot.id, _participacion_orm
        )
        _sincronizar(orm.evidencias, ot.evidencias, EvidenciaORM, ot.id, _evidencia_orm)
        self._s.flush()

    def listar(
        self,
        *,
        estado: EstadoOT | None = None,
        cliente_id: UUID | None = None,
        vehiculo_id: UUID | None = None,
        mecanico_id: UUID | None = None,
        del_dia: date | None = None,
    ) -> list[OrdenTrabajo]:
        stmt = select(OrdenTrabajoORM)
        if estado is not None:
            stmt = stmt.where(OrdenTrabajoORM.estado == estado.value)
        if cliente_id is not None:
            stmt = stmt.where(OrdenTrabajoORM.cliente_id == cliente_id)
        if vehiculo_id is not None:
            stmt = stmt.where(OrdenTrabajoORM.vehiculo_id == vehiculo_id)
        if del_dia is not None:
            stmt = stmt.where(func.date(OrdenTrabajoORM.fecha_ingreso) == del_dia)
        if mecanico_id is not None:
            subq = (
                select(ItemOTORM.ot_id)
                .where(ItemOTORM.mecanico_id == mecanico_id)
                .union(
                    select(ParticipacionORM.ot_id).where(
                        ParticipacionORM.mecanico_id == mecanico_id
                    )
                )
            )
            stmt = stmt.where(OrdenTrabajoORM.id.in_(subq))
        rows = self._s.scalars(stmt.order_by(OrdenTrabajoORM.numero.desc())).all()
        patentes = _patentes(self._s, {o.vehiculo_id for o in rows})
        return [_a_dominio(o, patentes.get(o.vehiculo_id)) for o in rows]

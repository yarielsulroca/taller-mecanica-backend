from __future__ import annotations

import uuid
from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import ComprobanteOrdenORM, ComprobanteORM
from taller.domain.entities.comprobante import Comprobante
from taller.domain.enums import (
    ClasificacionComprobante,
    CondicionPago,
    EstadoComprobante,
    OrigenComprobante,
    TipoComprobante,
)


def _a_dominio(o: ComprobanteORM) -> Comprobante:
    return Comprobante(
        id=o.id,
        tipo=TipoComprobante(o.tipo),
        clasificacion=ClasificacionComprobante(o.clasificacion),
        origen=OrigenComprobante(o.origen),
        fecha=o.fecha,
        total=o.total,
        emisor_cuit=o.emisor_cuit,
        emisor_razon_social=o.emisor_razon_social,
        receptor_tipo=o.receptor_tipo,
        receptor_id=o.receptor_id,
        receptor_nombre=o.receptor_nombre,
        pto_venta=o.pto_venta,
        numero=o.numero,
        cae=o.cae,
        neto=o.neto,
        iva21=o.iva21,
        iva105=o.iva105,
        iva27=o.iva27,
        no_gravado=o.no_gravado,
        percep_iva=o.percep_iva,
        percep_iibb=o.percep_iibb,
        condicion=CondicionPago(o.condicion),
        estado=EstadoComprobante(o.estado),
        archivo_path=o.archivo_path,
        observaciones=o.observaciones,
        creado_en=o.creado_en,
        ot_ids=[r.ot_id for r in o.ordenes],
    )


class SqlComprobanteRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, comprobante_id: UUID) -> Comprobante | None:
        orm = self._s.get(ComprobanteORM, comprobante_id)
        return _a_dominio(orm) if orm is not None else None

    def listar(
        self,
        *,
        clasificacion: ClasificacionComprobante | None = None,
        estado: EstadoComprobante | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        q: str | None = None,
    ) -> list[Comprobante]:
        stmt = select(ComprobanteORM)
        if clasificacion is not None:
            stmt = stmt.where(ComprobanteORM.clasificacion == clasificacion.value)
        if estado is not None:
            stmt = stmt.where(ComprobanteORM.estado == estado.value)
        if desde is not None:
            stmt = stmt.where(ComprobanteORM.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(ComprobanteORM.fecha <= hasta)
        if q:
            patron = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(ComprobanteORM.emisor_razon_social).like(patron),
                    func.lower(ComprobanteORM.receptor_nombre).like(patron),
                )
            )
        filas = self._s.scalars(stmt.order_by(ComprobanteORM.fecha.desc())).all()
        return [_a_dominio(o) for o in filas]

    def existe_fiscal(self, *, cuit_emisor: str, tipo: str, pto_venta: int, numero: int) -> bool:
        stmt = select(ComprobanteORM.id).where(
            ComprobanteORM.emisor_cuit == cuit_emisor,
            ComprobanteORM.tipo == tipo,
            ComprobanteORM.pto_venta == pto_venta,
            ComprobanteORM.numero == numero,
        )
        return self._s.scalar(stmt) is not None

    def guardar(self, comprobante: Comprobante) -> None:
        orm = self._s.get(ComprobanteORM, comprobante.id)
        if orm is None:
            orm = ComprobanteORM(id=comprobante.id)
            self._s.add(orm)
        orm.tipo = comprobante.tipo.value
        orm.clasificacion = comprobante.clasificacion.value
        orm.origen = comprobante.origen.value
        orm.es_fiscal = comprobante.es_fiscal
        orm.fecha = comprobante.fecha
        orm.emisor_cuit = comprobante.emisor_cuit
        orm.emisor_razon_social = comprobante.emisor_razon_social
        orm.receptor_tipo = comprobante.receptor_tipo
        orm.receptor_id = comprobante.receptor_id
        orm.receptor_nombre = comprobante.receptor_nombre
        orm.pto_venta = comprobante.pto_venta
        orm.numero = comprobante.numero
        orm.cae = comprobante.cae
        orm.neto = comprobante.neto
        orm.iva21 = comprobante.iva21
        orm.iva105 = comprobante.iva105
        orm.iva27 = comprobante.iva27
        orm.no_gravado = comprobante.no_gravado
        orm.percep_iva = comprobante.percep_iva
        orm.percep_iibb = comprobante.percep_iibb
        orm.total = comprobante.total
        orm.condicion = comprobante.condicion.value
        orm.estado = comprobante.estado.value
        orm.archivo_path = comprobante.archivo_path
        orm.observaciones = comprobante.observaciones
        orm.creado_en = comprobante.creado_en

        # H3: facturas ↔ OT (N:M, soporta flota sobre varias OT).
        por_ot = {r.ot_id: r for r in orm.ordenes}
        deseados = set(comprobante.ot_ids)
        for existente in [r for r in orm.ordenes if r.ot_id not in deseados]:
            orm.ordenes.remove(existente)
        for ot_id in deseados:
            if ot_id not in por_ot:
                orm.ordenes.append(
                    ComprobanteOrdenORM(id=uuid.uuid4(), comprobante_id=comprobante.id, ot_id=ot_id)
                )
        self._s.flush()

    def listar_por_orden(self, ot_id: UUID) -> list[Comprobante]:
        stmt = (
            select(ComprobanteORM)
            .join(ComprobanteOrdenORM, ComprobanteOrdenORM.comprobante_id == ComprobanteORM.id)
            .where(ComprobanteOrdenORM.ot_id == ot_id)
            .order_by(ComprobanteORM.fecha.desc())
        )
        return [_a_dominio(o) for o in self._s.scalars(stmt)]

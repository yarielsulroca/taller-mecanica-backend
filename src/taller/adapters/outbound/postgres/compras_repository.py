from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import CompraItemORM, CompraORM
from taller.domain.entities.compra import Compra, CompraItem
from taller.domain.enums import CondicionPago, EstadoCompra, TipoComprobante


def _item_dominio(o: CompraItemORM) -> CompraItem:
    return CompraItem(
        id=o.id,
        descripcion=o.descripcion,
        cantidad=o.cantidad,
        precio_unitario=o.precio_unitario,
        alicuota_iva=o.alicuota_iva,
        rubro_id=o.rubro_id,
        item_ot_id=o.item_ot_id,
    )


def _a_dominio(o: CompraORM) -> Compra:
    return Compra(
        id=o.id,
        proveedor_id=o.proveedor_id,
        ot_id=o.ot_id,
        fecha=o.fecha,
        condicion_pago=CondicionPago(o.condicion_pago),
        fecha_vencimiento=o.fecha_vencimiento,
        estado=EstadoCompra(o.estado),
        comprobante_path=o.comprobante_path,
        observaciones=o.observaciones,
        items=[_item_dominio(i) for i in o.items],
        creado_en=o.creado_en,
        tipo_comprobante=TipoComprobante(o.tipo_comprobante) if o.tipo_comprobante else None,
        pto_venta=o.pto_venta,
        numero=o.numero,
        comprobante_id=o.comprobante_id,
    )


class SqlCompraRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, compra_id: UUID) -> Compra | None:
        orm = self._s.get(CompraORM, compra_id)
        return _a_dominio(orm) if orm is not None else None

    def guardar(self, compra: Compra) -> None:
        orm = self._s.get(CompraORM, compra.id)
        if orm is None:
            orm = CompraORM(id=compra.id)
            self._s.add(orm)
        orm.proveedor_id = compra.proveedor_id
        orm.ot_id = compra.ot_id
        orm.fecha = compra.fecha
        orm.condicion_pago = compra.condicion_pago.value
        orm.fecha_vencimiento = compra.fecha_vencimiento
        orm.estado = compra.estado.value
        orm.neto = compra.neto
        orm.iva = compra.iva
        orm.total = compra.total
        orm.tipo_comprobante = compra.tipo_comprobante.value if compra.tipo_comprobante else None
        orm.pto_venta = compra.pto_venta
        orm.numero = compra.numero
        orm.comprobante_id = compra.comprobante_id
        orm.comprobante_path = compra.comprobante_path
        orm.observaciones = compra.observaciones
        orm.creado_en = compra.creado_en

        por_id = {c.id: c for c in orm.items}
        deseados = {i.id for i in compra.items}
        for existente in [c for c in orm.items if c.id not in deseados]:
            orm.items.remove(existente)
        for item in compra.items:
            fila = por_id.get(item.id)
            if fila is None:
                fila = CompraItemORM(id=item.id, compra_id=compra.id)
                orm.items.append(fila)
            fila.descripcion = item.descripcion
            fila.cantidad = item.cantidad
            fila.precio_unitario = item.precio_unitario
            fila.alicuota_iva = item.alicuota_iva
            fila.rubro_id = item.rubro_id
            fila.item_ot_id = item.item_ot_id
        self._s.flush()

    def listar(
        self,
        *,
        proveedor_id: UUID | None = None,
        ot_id: UUID | None = None,
        estado: EstadoCompra | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[Compra]:
        stmt = select(CompraORM)
        if proveedor_id is not None:
            stmt = stmt.where(CompraORM.proveedor_id == proveedor_id)
        if ot_id is not None:
            stmt = stmt.where(CompraORM.ot_id == ot_id)
        if estado is not None:
            stmt = stmt.where(CompraORM.estado == estado.value)
        if desde is not None:
            stmt = stmt.where(CompraORM.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(CompraORM.fecha <= hasta)
        filas = self._s.scalars(stmt.order_by(CompraORM.fecha.desc())).all()
        return [_a_dominio(o) for o in filas]

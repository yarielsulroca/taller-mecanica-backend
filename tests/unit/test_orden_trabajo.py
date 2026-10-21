from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.domain.entities.orden_trabajo import ItemOT, OrdenTrabajo
from taller.domain.enums import EstadoItem, EstadoOT, OrigenPieza, TipoItem
from taller.domain.exceptions import EstadoInvalido, OTCerrada, SolicitudInvalida


def _item(
    precio: str = "100",
    tipo: TipoItem = TipoItem.MANO_OBRA,
    **extra: object,
) -> ItemOT:
    return ItemOT(  # type: ignore[arg-type]
        descripcion="Cambio de aceite",
        tipo=tipo,
        precio_unitario=Decimal(precio),
        **extra,  # type: ignore[arg-type]
    )


def _ot() -> OrdenTrabajo:
    return OrdenTrabajo(vehiculo_id=uuid4(), cliente_id=uuid4(), numero=1, km_ingreso=1000)


def test_operacion_sin_precio_no_suma_al_total() -> None:
    ot = _ot()
    sin_precio = ItemOT(descripcion="Revisión general", tipo=TipoItem.MANO_OBRA)
    con_precio = ItemOT(
        descripcion="Cambio de buje", tipo=TipoItem.MANO_OBRA, precio_unitario=Decimal("800")
    )
    ot.agregar_item(sin_precio)
    ot.agregar_item(con_precio)
    assert sin_precio.tiene_precio is False
    assert con_precio.tiene_precio is True
    assert ot.total == Decimal("800.00")


def test_repuesto_exige_origen() -> None:
    with pytest.raises(SolicitudInvalida):
        _item(tipo=TipoItem.REPUESTO)


def test_origen_solo_para_repuestos() -> None:
    with pytest.raises(SolicitudInvalida):
        _item(tipo=TipoItem.MANO_OBRA, origen_pieza=OrigenPieza.TALLER)


def test_subtotal_y_totales() -> None:
    ot = _ot()
    ot.agregar_item(
        ItemOT(
            descripcion="Mano de obra",
            tipo=TipoItem.MANO_OBRA,
            cantidad=Decimal("2"),
            precio_unitario=Decimal("500"),
        )
    )
    ot.agregar_item(
        ItemOT(
            descripcion="Filtro",
            tipo=TipoItem.REPUESTO,
            precio_unitario=Decimal("1000"),
            origen_pieza=OrigenPieza.TALLER,
        )
    )
    assert ot.total_mano_obra == Decimal("1000.00")
    assert ot.total_repuestos == Decimal("1000.00")
    assert ot.total == Decimal("2000.00")


def test_no_presupuestar_sin_items_con_precio() -> None:
    ot = _ot()
    ot.iniciar_revision()
    with pytest.raises(EstadoInvalido):
        ot.presupuestar()


def test_flujo_completo_hasta_pendiente_pago() -> None:
    ot = _ot()
    ot.iniciar_revision()
    ot.agregar_item(_item())
    ot.presupuestar()
    assert ot.estado == EstadoOT.PRESUPUESTADO

    ot.registrar_aprobacion(uuid4(), "telefono", datetime.now(UTC))
    assert ot.estado == EstadoOT.EN_TALLER

    ot.items[0].completar()
    ot.validar_cierre(uuid4(), datetime.now(UTC), "todo ok")
    assert ot.estado == EstadoOT.PENDIENTE_PAGO
    assert ot.validado_por is not None


def test_no_validar_con_operaciones_pendientes() -> None:
    ot = _ot()
    ot.iniciar_revision()
    ot.agregar_item(_item())
    ot.presupuestar()
    ot.registrar_aprobacion(uuid4(), "whatsapp", datetime.now(UTC))
    with pytest.raises(EstadoInvalido):
        ot.validar_cierre(uuid4(), datetime.now(UTC))


def test_transicion_invalida() -> None:
    ot = _ot()
    with pytest.raises(EstadoInvalido):
        ot.presupuestar()  # no se puede saltar de iniciado a presupuestado


def test_ot_cancelada_no_editable() -> None:
    ot = _ot()
    ot.cancelar()
    with pytest.raises(OTCerrada):
        ot.agregar_item(_item())


def test_marcar_no_realizado_exige_motivo() -> None:
    item = _item()
    with pytest.raises(SolicitudInvalida):
        item.marcar_no_realizado("")
    item.marcar_no_realizado("El cliente no quiso")
    assert item.estado == EstadoItem.NO_REALIZADO

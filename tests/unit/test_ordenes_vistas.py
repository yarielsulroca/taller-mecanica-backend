from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from taller.adapters.inbound.api.schemas_ordenes import OTResponse, OTResponseOperativa
from taller.domain.entities.orden_trabajo import ItemOT, OrdenTrabajo
from taller.domain.enums import TipoItem


def _ot() -> OrdenTrabajo:
    ot = OrdenTrabajo(vehiculo_id=uuid4(), cliente_id=uuid4(), numero=1, km_ingreso=1000)
    ot.agregar_item(
        ItemOT(
            descripcion="Cambio de aceite",
            tipo=TipoItem.MANO_OBRA,
            precio_unitario=Decimal("500"),
        )
    )
    return ot


def test_vista_operativa_no_expone_importes() -> None:
    data = OTResponseOperativa.from_domain(_ot()).model_dump()
    assert "total" not in data
    assert "total_mano_obra" not in data
    assert "precio_unitario" not in data["items"][0]
    assert "descuento" not in data["items"][0]
    assert "subtotal" not in data["items"][0]
    # El mecánico sí ve el listado de operaciones.
    assert data["items"][0]["descripcion"] == "Cambio de aceite"


def test_vista_completa_expone_importes() -> None:
    data = OTResponse.from_domain(_ot()).model_dump()
    assert data["total"] == Decimal("500.00")
    assert data["items"][0]["precio_unitario"] == Decimal("500")

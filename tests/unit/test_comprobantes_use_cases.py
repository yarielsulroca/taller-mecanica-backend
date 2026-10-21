from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.application.use_cases.comprobantes import (
    ListarComprobantes,
    ListarComprobantesQuery,
    RegistrarComprobante,
    RegistrarComprobanteCommand,
)
from taller.domain.entities.configuracion import ConfiguracionTaller, PuntoVentaTaller
from taller.domain.enums import (
    ClasificacionComprobante,
    CondicionIva,
    EstadoComprobante,
    OrigenComprobante,
    TipoComprobante,
)
from taller.domain.exceptions import Conflicto, FacturaDuplicada, SolicitudInvalida
from taller.domain.value_objects.cuit import Cuit
from tests.fakes_comprobantes import FakeComprobanteRepository
from tests.fakes_configuracion import FakeConfiguracionTallerRepository


def _cmd(**extra: object) -> RegistrarComprobanteCommand:
    base: dict[str, object] = {
        "tipo": TipoComprobante.FACTURA_A,
        "clasificacion": ClasificacionComprobante.COMPRA,
        "fecha": date(2026, 9, 11),
        "total": Decimal("60500.00"),
        "emisor_cuit": "20123456783",
        "pto_venta": 3,
        "numero": 123,
        "neto": Decimal("50000.00"),
        "iva21": Decimal("10500.00"),
    }
    base.update(extra)
    return RegistrarComprobanteCommand(**base)  # type: ignore[arg-type]


def test_registrar_completa_neto_por_defecto() -> None:
    repo = FakeComprobanteRepository()
    comprobante = RegistrarComprobante(repo).execute(
        RegistrarComprobanteCommand(
            tipo=TipoComprobante.TICKET,
            clasificacion=ClasificacionComprobante.COMPRA,
            fecha=date(2026, 9, 11),
            total=Decimal("1500.00"),
        )
    )
    assert comprobante.neto == Decimal("1500.00")
    assert comprobante.estado == EstadoComprobante.PENDIENTE


def test_fiscal_sin_datos_falla() -> None:
    repo = FakeComprobanteRepository()
    with pytest.raises(SolicitudInvalida):
        RegistrarComprobante(repo).execute(
            RegistrarComprobanteCommand(
                tipo=TipoComprobante.FACTURA_A,
                clasificacion=ClasificacionComprobante.COMPRA,
                fecha=date(2026, 9, 11),
                total=Decimal("100.00"),
                neto=Decimal("100.00"),
            )
        )


def test_unicidad_fiscal() -> None:
    repo = FakeComprobanteRepository()
    RegistrarComprobante(repo).execute(_cmd())
    with pytest.raises(FacturaDuplicada):
        RegistrarComprobante(repo).execute(_cmd())


def test_listar_por_clasificacion() -> None:
    repo = FakeComprobanteRepository()
    RegistrarComprobante(repo).execute(_cmd())
    RegistrarComprobante(repo).execute(
        RegistrarComprobanteCommand(
            tipo=TipoComprobante.RECIBO,
            clasificacion=ClasificacionComprobante.PAGO,
            fecha=date(2026, 9, 12),
            total=Decimal("2000.00"),
        )
    )
    pagos = ListarComprobantes(repo).execute(
        ListarComprobantesQuery(clasificacion=ClasificacionComprobante.PAGO)
    )
    assert len(pagos) == 1
    assert pagos[0].clasificacion == ClasificacionComprobante.PAGO


def test_factura_a_pedido_y_comprobante_del_cliente_en_la_misma_lista() -> None:
    repo = FakeComprobanteRepository()
    # El taller emite la factura de venta a pedido del cliente.
    RegistrarComprobante(repo).execute(
        RegistrarComprobanteCommand(
            tipo=TipoComprobante.FACTURA_B,
            clasificacion=ClasificacionComprobante.VENTA,
            origen=OrigenComprobante.TALLER,
            fecha=date(2026, 9, 11),
            total=Decimal("60500.00"),
            emisor_cuit="20123456783",
            pto_venta=1,
            numero=1,
            neto=Decimal("50000.00"),
            iva21=Decimal("10500.00"),
        )
    )
    # El cliente paga y aporta su comprobante (transferencia/Mercado Pago).
    RegistrarComprobante(repo).execute(
        RegistrarComprobanteCommand(
            tipo=TipoComprobante.RECIBO,
            clasificacion=ClasificacionComprobante.PAGO,
            origen=OrigenComprobante.CLIENTE,
            fecha=date(2026, 9, 11),
            total=Decimal("60500.00"),
        )
    )
    todos = ListarComprobantes(repo).execute(ListarComprobantesQuery())
    assert len(todos) == 2
    origenes = {c.origen for c in todos}
    assert origenes == {OrigenComprobante.TALLER, OrigenComprobante.CLIENTE}


# --- H1/H2/H3: reglas fiscales de la configuración del taller ---------------
def _configurar(
    cond_iva: CondicionIva, *, puntos: tuple[int, ...] = (1,)
) -> FakeConfiguracionTallerRepository:
    return FakeConfiguracionTallerRepository(
        ConfiguracionTaller(
            razon_social="Taller Rossi",
            cuit=Cuit("20123456783"),
            cond_iva=cond_iva,
            puntos_venta=[PuntoVentaTaller(numero=n) for n in puntos],
        )
    )


def test_venta_monotributo_rellena_emisor_y_vincula_ots() -> None:
    repo = FakeComprobanteRepository()
    ot_id = uuid4()
    comprobante = RegistrarComprobante(repo, _configurar(CondicionIva.MONOTRIBUTO)).execute(
        RegistrarComprobanteCommand(
            tipo=TipoComprobante.FACTURA_C,
            clasificacion=ClasificacionComprobante.VENTA,
            fecha=date(2026, 9, 11),
            total=Decimal("1210.00"),
            pto_venta=1,
            numero=1,
            receptor_nombre="Juan Pérez",
            ot_ids=(ot_id,),
        )
    )
    # H1: el emisor es el taller (siempre facturas de venta).
    assert comprobante.emisor_cuit == "20123456783"
    assert comprobante.emisor_razon_social == "Taller Rossi"
    # H3: la factura queda asociada a la OT.
    assert comprobante.ot_ids == [ot_id]


def test_monotributo_no_puede_emitir_factura_a() -> None:
    repo = FakeComprobanteRepository()
    with pytest.raises(SolicitudInvalida):
        RegistrarComprobante(repo, _configurar(CondicionIva.MONOTRIBUTO)).execute(
            RegistrarComprobanteCommand(
                tipo=TipoComprobante.FACTURA_A,
                clasificacion=ClasificacionComprobante.VENTA,
                fecha=date(2026, 9, 11),
                total=Decimal("1000.00"),
                pto_venta=1,
                numero=1,
                cond_iva_receptor=CondicionIva.RESPONSABLE_INSCRIPTO,
                emisor_cuit="20123456783",
            )
        )


def test_ri_con_receptor_ri_es_factura_a() -> None:
    repo = FakeComprobanteRepository()
    comprobante = RegistrarComprobante(
        repo, _configurar(CondicionIva.RESPONSABLE_INSCRIPTO)
    ).execute(
        RegistrarComprobanteCommand(
            tipo=TipoComprobante.FACTURA_A,
            clasificacion=ClasificacionComprobante.VENTA,
            fecha=date(2026, 9, 11),
            total=Decimal("1210.00"),
            pto_venta=1,
            numero=1,
            cond_iva_receptor=CondicionIva.RESPONSABLE_INSCRIPTO,
        )
    )
    assert comprobante.tipo == TipoComprobante.FACTURA_A


def test_punto_venta_no_habilitado_falla() -> None:
    repo = FakeComprobanteRepository()
    with pytest.raises(Conflicto):
        RegistrarComprobante(repo, _configurar(CondicionIva.MONOTRIBUTO, puntos=(2,))).execute(
            RegistrarComprobanteCommand(
                tipo=TipoComprobante.FACTURA_C,
                clasificacion=ClasificacionComprobante.VENTA,
                fecha=date(2026, 9, 11),
                total=Decimal("1000.00"),
                pto_venta=1,
                numero=1,
            )
        )

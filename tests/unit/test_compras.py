from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.application.use_cases.compras import (
    AnularCompra,
    ItemCompraCommand,
    RegistrarCompra,
    RegistrarCompraCommand,
    RegistrarPagoCompra,
    RegistrarPagoCompraCommand,
)
from taller.domain.entities.compra import CompraItem
from taller.domain.entities.configuracion import ConfiguracionTaller, PuntoVentaTaller
from taller.domain.entities.proveedor import Proveedor
from taller.domain.enums import (
    ClasificacionComprobante,
    CondicionIva,
    CondicionPago,
    EstadoCompra,
    EstadoCuota,
    NaturalezaMovimiento,
    OrigenCuota,
    Periodicidad,
    SignoMovimiento,
    TipoComprobante,
)
from taller.domain.exceptions import (
    Conflicto,
    FacturaDuplicada,
    NoEncontrado,
    SolicitudInvalida,
)
from taller.domain.value_objects.cuit import Cuit
from tests.fakes_compras import FakeCompraRepository
from tests.fakes_comprobantes import FakeComprobanteRepository
from tests.fakes_configuracion import FakeConfiguracionTallerRepository
from tests.fakes_finanzas import FakeCuotaRepository, FakeMovimientoRepository
from tests.fakes_maestros import FakeProveedorRepository


def _setup():
    proveedor = Proveedor(razon_social="Repuestos SA", cuit=Cuit("30712345678"))
    proveedores = FakeProveedorRepository([proveedor])
    compras = FakeCompraRepository()
    cuotas = FakeCuotaRepository()
    movimientos = FakeMovimientoRepository()
    return proveedor, proveedores, compras, cuotas, movimientos


def _item(precio: str = "1000", alicuota: str = "21") -> ItemCompraCommand:
    return ItemCompraCommand(
        descripcion="Filtro de aceite",
        cantidad=Decimal("1"),
        precio_unitario=Decimal(precio),
        alicuota_iva=Decimal(alicuota),
    )


def test_item_calcula_iva_y_total() -> None:
    item = CompraItem(
        descripcion="Filtro",
        cantidad=Decimal("2"),
        precio_unitario=Decimal("100"),
        alicuota_iva=Decimal("21"),
    )
    assert item.subtotal == Decimal("200.00")
    assert item.iva_monto == Decimal("42.00")
    assert item.total == Decimal("242.00")


def test_item_alicuota_invalida() -> None:
    with pytest.raises(SolicitudInvalida):
        CompraItem(
            descripcion="X",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1"),
            alicuota_iva=Decimal("15"),
        )


def test_registrar_compra_contado_genera_una_cuota() -> None:
    proveedor, proveedores, compras, cuotas, _ = _setup()
    compra = RegistrarCompra(compras, cuotas, proveedores).execute(
        RegistrarCompraCommand(
            proveedor_id=proveedor.id,
            fecha=date(2026, 10, 6),
            items=(_item(),),
        )
    )
    assert compra.neto == Decimal("1000.00")
    assert compra.iva == Decimal("210.00")
    assert compra.total == Decimal("1210.00")
    assert len(cuotas.listar(referencia_id=compra.id, origen=OrigenCuota.PAGO)) == 1


def test_registrar_compra_cuenta_corriente_con_plan() -> None:
    proveedor, proveedores, compras, cuotas, _ = _setup()
    compra = RegistrarCompra(compras, cuotas, proveedores).execute(
        RegistrarCompraCommand(
            proveedor_id=proveedor.id,
            fecha=date(2026, 10, 6),
            items=(_item(precio="1000", alicuota="0"),),
            condicion_pago=CondicionPago.CUENTA_CORRIENTE,
            fecha_vencimiento=date(2026, 11, 6),
            plan_periodicidad=Periodicidad.MENSUAL,
            plan_cantidad=3,
        )
    )
    plan = cuotas.listar(referencia_id=compra.id, origen=OrigenCuota.PAGO)
    assert len(plan) == 3
    assert sum((c.monto for c in plan), Decimal("0.00")) == Decimal("1000.00")


def test_compra_cuenta_corriente_sin_vencimiento_falla() -> None:
    proveedor, proveedores, compras, cuotas, _ = _setup()
    with pytest.raises(SolicitudInvalida):
        RegistrarCompra(compras, cuotas, proveedores).execute(
            RegistrarCompraCommand(
                proveedor_id=proveedor.id,
                fecha=date(2026, 10, 6),
                items=(_item(),),
                condicion_pago=CondicionPago.CUENTA_CORRIENTE,
            )
        )


def test_compra_proveedor_inexistente() -> None:
    _, proveedores, compras, cuotas, _ = _setup()
    with pytest.raises(NoEncontrado):
        RegistrarCompra(compras, cuotas, proveedores).execute(
            RegistrarCompraCommand(proveedor_id=uuid4(), fecha=date(2026, 10, 6), items=(_item(),))
        )


def test_pagar_compra_parcial_y_total() -> None:
    proveedor, proveedores, compras, cuotas, movimientos = _setup()
    compra = RegistrarCompra(compras, cuotas, proveedores).execute(
        RegistrarCompraCommand(
            proveedor_id=proveedor.id,
            fecha=date(2026, 10, 6),
            items=(_item(precio="1000", alicuota="0"),),
        )
    )
    pagar = RegistrarPagoCompra(compras, cuotas, movimientos)
    parcial = pagar.execute(
        RegistrarPagoCompraCommand(
            compra_id=compra.id, fecha=date(2026, 10, 6), monto=Decimal("400")
        )
    )
    assert parcial.estado == EstadoCompra.PARCIAL
    total = pagar.execute(
        RegistrarPagoCompraCommand(
            compra_id=compra.id, fecha=date(2026, 10, 7), monto=Decimal("600")
        )
    )
    assert total.estado == EstadoCompra.PAGADA
    assert len(movimientos.listar(signo=SignoMovimiento.EGRESO)) == 2
    assert movimientos.listar()[0].naturaleza == NaturalezaMovimiento.PAGO_PROVEEDOR


def test_pago_que_excede_saldo_falla() -> None:
    proveedor, proveedores, compras, cuotas, movimientos = _setup()
    compra = RegistrarCompra(compras, cuotas, proveedores).execute(
        RegistrarCompraCommand(
            proveedor_id=proveedor.id,
            fecha=date(2026, 10, 6),
            items=(_item(precio="100", alicuota="0"),),
        )
    )
    with pytest.raises(Conflicto):
        RegistrarPagoCompra(compras, cuotas, movimientos).execute(
            RegistrarPagoCompraCommand(
                compra_id=compra.id, fecha=date(2026, 10, 6), monto=Decimal("999")
            )
        )


def test_anular_compra_anula_cuotas() -> None:
    proveedor, proveedores, compras, cuotas, _ = _setup()
    compra = RegistrarCompra(compras, cuotas, proveedores).execute(
        RegistrarCompraCommand(proveedor_id=proveedor.id, fecha=date(2026, 10, 6), items=(_item(),))
    )
    AnularCompra(compras, cuotas).execute(compra.id)
    assert compra.estado == EstadoCompra.ANULADA
    assert all(c.estado == EstadoCuota.ANULADA for c in cuotas.listar(referencia_id=compra.id))


# --- H4: la compra con datos fiscales fluye a la tabla de comprobantes ------
def _setup_fiscal(
    cond_taller: CondicionIva = CondicionIva.MONOTRIBUTO,
    cond_proveedor: CondicionIva = CondicionIva.RESPONSABLE_INSCRIPTO,
) -> tuple[RegistrarCompra, FakeCompraRepository, FakeComprobanteRepository, Proveedor]:
    proveedor = Proveedor(
        razon_social="Repuestos SA", cuit=Cuit("30712345678"), cond_iva=cond_proveedor
    )
    config = ConfiguracionTaller(
        razon_social="Taller Rossi",
        cuit=Cuit("20123456783"),
        cond_iva=cond_taller,
        puntos_venta=[PuntoVentaTaller(numero=1)],
    )
    compras = FakeCompraRepository()
    comprobantes = FakeComprobanteRepository()
    uc = RegistrarCompra(
        compras,
        FakeCuotaRepository(),
        FakeProveedorRepository([proveedor]),
        comprobantes,
        FakeConfiguracionTallerRepository(config),
    )
    return uc, compras, comprobantes, proveedor


def test_compra_factura_b_genera_comprobante_vinculado() -> None:
    uc, compras, comprobantes, proveedor = _setup_fiscal()
    compra = uc.execute(
        RegistrarCompraCommand(
            proveedor_id=proveedor.id,
            fecha=date(2026, 10, 6),
            items=(_item(),),
            tipo_comprobante=TipoComprobante.FACTURA_B,
            pto_venta=1,
            numero=100,
        )
    )
    assert compra.tipo_comprobante == TipoComprobante.FACTURA_B
    assert compra.comprobante_id is not None
    registrada = comprobantes.obtener(compra.comprobante_id)
    assert registrada is not None
    assert registrada.clasificacion == ClasificacionComprobante.COMPRA
    assert registrada.emisor_cuit == "30712345678"
    assert registrada.receptor_tipo == "taller"
    # El desglose de IVA se copia por alícuota.
    assert registrada.neto == Decimal("1000.00")
    assert registrada.iva21 == Decimal("210.00")
    assert registrada.total == compra.total


def test_compra_factura_vincula_ots() -> None:
    uc, compras, comprobantes, proveedor = _setup_fiscal()
    ot_id = uuid4()
    compra = uc.execute(
        RegistrarCompraCommand(
            proveedor_id=proveedor.id,
            fecha=date(2026, 10, 6),
            items=(_item(),),
            ot_id=ot_id,
            tipo_comprobante=TipoComprobante.FACTURA_B,
            pto_venta=1,
            numero=101,
        )
    )
    registrada = comprobantes.obtener(compra.comprobante_id)  # type: ignore[arg-type]
    assert registrada is not None and registrada.ot_ids == [ot_id]


def test_factura_compra_duplicada_falla() -> None:
    uc, _, _, proveedor = _setup_fiscal()
    cmd = RegistrarCompraCommand(
        proveedor_id=proveedor.id,
        fecha=date(2026, 10, 6),
        items=(_item(),),
        tipo_comprobante=TipoComprobante.FACTURA_B,
        pto_venta=1,
        numero=100,
    )
    uc.execute(cmd)
    with pytest.raises(FacturaDuplicada):
        uc.execute(cmd)


def test_factura_compra_tipo_inconsistente_falla() -> None:
    # Proveedor RI (emisor) + taller monotributo (receptor) → corresponde B.
    uc, _, _, proveedor = _setup_fiscal(
        cond_taller=CondicionIva.MONOTRIBUTO,
        cond_proveedor=CondicionIva.RESPONSABLE_INSCRIPTO,
    )
    with pytest.raises(SolicitudInvalida):
        uc.execute(
            RegistrarCompraCommand(
                proveedor_id=proveedor.id,
                fecha=date(2026, 10, 6),
                items=(_item(),),
                tipo_comprobante=TipoComprobante.FACTURA_A,
                pto_venta=1,
                numero=102,
            )
        )


def test_compra_sin_fiscal_no_genera_comprobante() -> None:
    proveedor, proveedores, compras, cuotas, _ = _setup()
    uc = RegistrarCompra(compras, cuotas, proveedores)
    compra = uc.execute(
        RegistrarCompraCommand(proveedor_id=proveedor.id, fecha=date(2026, 10, 6), items=(_item(),))
    )
    assert compra.tipo_comprobante is None
    assert compra.comprobante_id is None

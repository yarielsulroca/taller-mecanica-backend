from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from taller.application.use_cases.reportes import (
    CuentasPorCobrar,
    CuentasPorPagar,
    DashboardFinanciero,
    ExportarMovimientos,
    ObtenerRentabilidadOT,
    ObtenerResumenIva,
)
from taller.domain.entities.comprobante import Comprobante
from taller.domain.entities.movimiento import Cuota, Movimiento
from taller.domain.entities.orden_trabajo import ItemOT, OrdenTrabajo
from taller.domain.enums import (
    ClasificacionComprobante,
    EstadoMovimiento,
    MedioPago,
    NaturalezaMovimiento,
    OrigenCuota,
    SignoMovimiento,
    TipoComprobante,
    TipoItem,
)
from tests.fakes_comprobantes import FakeComprobanteRepository
from tests.fakes_finanzas import FakeCuotaRepository, FakeMovimientoRepository
from tests.fakes_ordenes import FakeOrdenTrabajoRepository


def _movimiento(
    signo: SignoMovimiento,
    monto: str,
    *,
    estado: EstadoMovimiento = EstadoMovimiento.COMPROBADO,
    ot_id=None,
) -> Movimiento:
    return Movimiento(
        fecha=date(2026, 10, 6),
        signo=signo,
        naturaleza=NaturalezaMovimiento.OTRO,
        monto=Decimal(monto),
        medio=MedioPago.EFECTIVO,
        estado=estado,
        ot_id=ot_id,
    )


def test_dashboard_financiero() -> None:
    movimientos = FakeMovimientoRepository()
    movimientos.guardar(_movimiento(SignoMovimiento.INGRESO, "1000"))
    movimientos.guardar(_movimiento(SignoMovimiento.EGRESO, "400"))
    movimientos.guardar(
        _movimiento(SignoMovimiento.INGRESO, "500", estado=EstadoMovimiento.PENDIENTE)
    )
    cuotas = FakeCuotaRepository()
    cuotas.guardar(
        Cuota(
            origen=OrigenCuota.COBRO,
            referencia_tipo="comprobante",
            referencia_id=uuid4(),
            numero=1,
            fecha_vencimiento=date(2026, 12, 1),
            monto=Decimal("300"),
            cliente_id=uuid4(),
        )
    )
    cuotas.guardar(
        Cuota(
            origen=OrigenCuota.PAGO,
            referencia_tipo="compra",
            referencia_id=uuid4(),
            numero=1,
            fecha_vencimiento=date(2026, 12, 1),
            monto=Decimal("200"),
            proveedor_id=uuid4(),
        )
    )
    ordenes = FakeOrdenTrabajoRepository()
    ordenes.guardar(OrdenTrabajo(vehiculo_id=uuid4(), cliente_id=uuid4(), numero=1))

    resumen = DashboardFinanciero(movimientos, cuotas, ordenes).execute()
    assert resumen.ingresos == Decimal("1000")
    assert resumen.egresos == Decimal("400")
    assert resumen.resultado == Decimal("600")
    assert resumen.cuentas_por_cobrar == Decimal("300")
    assert resumen.cuentas_por_pagar == Decimal("200")
    assert resumen.ot_abiertas == 1


def test_rentabilidad_ot() -> None:
    ot = OrdenTrabajo(vehiculo_id=uuid4(), cliente_id=uuid4(), numero=1)
    ot.agregar_item(
        ItemOT(descripcion="Mano de obra", tipo=TipoItem.MANO_OBRA, precio_unitario=Decimal("1500"))
    )
    ordenes = FakeOrdenTrabajoRepository([ot])
    movimientos = FakeMovimientoRepository()
    movimientos.guardar(_movimiento(SignoMovimiento.INGRESO, "1500", ot_id=ot.id))
    movimientos.guardar(_movimiento(SignoMovimiento.EGRESO, "500", ot_id=ot.id))

    rent = ObtenerRentabilidadOT(movimientos, ordenes).execute(ot.id)
    assert rent.presupuestado == Decimal("1500.00")
    assert rent.ingresos == Decimal("1500")
    assert rent.costos == Decimal("500")
    assert rent.resultado == Decimal("1000")


def test_cuentas_por_cobrar_y_pagar() -> None:
    cuotas = FakeCuotaRepository()
    cliente = uuid4()
    proveedor = uuid4()
    cuotas.guardar(
        Cuota(
            origen=OrigenCuota.COBRO,
            referencia_tipo="comprobante",
            referencia_id=uuid4(),
            numero=1,
            fecha_vencimiento=date(2026, 12, 1),
            monto=Decimal("300"),
            cliente_id=cliente,
        )
    )
    cuotas.guardar(
        Cuota(
            origen=OrigenCuota.PAGO,
            referencia_tipo="compra",
            referencia_id=uuid4(),
            numero=1,
            fecha_vencimiento=date(2026, 12, 1),
            monto=Decimal("200"),
            proveedor_id=proveedor,
        )
    )
    assert CuentasPorCobrar(cuotas).execute()[0].referencia_id == cliente
    assert CuentasPorPagar(cuotas).execute()[0].referencia_id == proveedor


def test_resumen_iva() -> None:
    repo = FakeComprobanteRepository()
    repo.guardar(
        Comprobante(
            tipo=TipoComprobante.FACTURA_A,
            clasificacion=ClasificacionComprobante.VENTA,
            fecha=date(2026, 10, 6),
            total=Decimal("1210.00"),
            neto=Decimal("1000.00"),
            iva21=Decimal("210.00"),
        )
    )
    repo.guardar(
        Comprobante(
            tipo=TipoComprobante.FACTURA_A,
            clasificacion=ClasificacionComprobante.COMPRA,
            fecha=date(2026, 10, 6),
            total=Decimal("605.00"),
            neto=Decimal("500.00"),
            iva21=Decimal("105.00"),
        )
    )
    resumen = ObtenerResumenIva(repo).execute()
    assert resumen.debito_fiscal == Decimal("210.00")
    assert resumen.credito_fiscal == Decimal("105.00")
    assert resumen.saldo == Decimal("105.00")


def test_exportar_movimientos_csv() -> None:
    movimientos = FakeMovimientoRepository()
    movimientos.guardar(_movimiento(SignoMovimiento.INGRESO, "1000"))
    csv_texto = ExportarMovimientos(movimientos).execute()
    assert "fecha,signo,naturaleza" in csv_texto
    assert "ingreso" in csv_texto

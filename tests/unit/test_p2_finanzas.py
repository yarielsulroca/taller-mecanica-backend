from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.application.use_cases.cobros import (
    RegistrarCobro,
    RegistrarCobroCommand,
    RetencionCommand,
)
from taller.application.use_cases.compras import (
    RegistrarPagoCompra,
    RegistrarPagoCompraCommand,
)
from taller.domain.entities.cliente import Cliente
from taller.domain.entities.movimiento import (
    Cuota,
    Movimiento,
    Retencion,
    generar_cuotas,
)
from taller.domain.entities.proveedor import Proveedor
from taller.domain.enums import (
    CondicionIva,
    EstadoCompra,
    EstadoCuota,
    MedioPago,
    NaturalezaMovimiento,
    OrigenCuota,
    Periodicidad,
    RetencionTipo,
    SignoMovimiento,
    TipoDocumento,
)
from taller.domain.exceptions import Conflicto, SolicitudInvalida
from tests.fakes import FakeClock
from tests.fakes_compras import FakeCompraRepository
from tests.fakes_finanzas import FakeCuotaRepository, FakeMovimientoRepository
from tests.fakes_maestros import FakeClienteRepository


def _cliente() -> Cliente:
    return Cliente(
        nombre="Cooperativa SL",
        tipo_doc=TipoDocumento.CUIT,
        nro_doc="30712345678",
        cond_iva=CondicionIva.RESPONSABLE_INSCRIPTO,
    )


def _retencion(monto: str = "500", tipo: RetencionTipo = RetencionTipo.IIBB) -> RetencionCommand:
    return RetencionCommand(tipo=tipo, monto=Decimal(monto), certificado="CERT-001")


# --- Dominio ----------------------------------------------------------------
def test_retencion_monto_invalido_falla() -> None:
    with pytest.raises(SolicitudInvalida):
        Retencion(tipo=RetencionTipo.IIBB, monto=Decimal("0"))
    with pytest.raises(SolicitudInvalida):
        Retencion(tipo=RetencionTipo.IVA, monto=Decimal("-5"))


def test_movimiento_importe_imputado() -> None:
    """El cobro imputa efectivo + certificados (H5); el flujo de caja es el neto."""
    mov = Movimiento(
        fecha=date(2026, 10, 6),
        signo=SignoMovimiento.INGRESO,
        naturaleza=NaturalezaMovimiento.VENTA_TRABAJO,
        monto=Decimal("60000"),
        retenciones=[
            Retencion(tipo=RetencionTipo.IIBB, monto=Decimal("500.00"), certificado="74-1"),
            Retencion(tipo=RetencionTipo.GANANCIAS, monto=Decimal("300.00"), certificado="GA-9"),
        ],
    )
    assert mov.total_retenciones == Decimal("800.00")
    assert mov.importe_imputado == Decimal("60800.00")
    assert mov.monto == Decimal("60000.00")  # caja: lo que realmente entró


# --- Caso de uso: cobro con retenciones contra cuota ------------------------
def test_cobro_con_retenciones_salda_la_cuota() -> None:
    cliente = _cliente()
    clientes = FakeClienteRepository([cliente])
    cuotas = CuotaGenerosa()
    movimientos = FakeMovimientoRepository()
    cobro = RegistrarCobro(
        clientes,
        movimientos,
        cuotas,
        _adjuntos_nulos(),  # no adjuntos en este caso
        _storage_nulo(),
        FakeClock(),
    )
    cuota_id = cuotas.crear_pendiente(cliente.id, Decimal("60800.00"))
    mov = cobro.execute(
        RegistrarCobroCommand(
            cliente_id=cliente.id,
            fecha=date(2026, 10, 6),
            monto=Decimal("60000.00"),
            medio=MedioPago.TRANSFERENCIA,
            cuota_id=cuota_id,
            retenciones=(_retencion(), _retencion("300", RetencionTipo.GANANCIAS)),
        )
    )
    assert mov.total_retenciones == Decimal("800.00")
    cuota = cuotas.obtener(cuota_id)
    assert cuota is not None and cuota.estado == EstadoCuota.PAGADA
    assert cuota.saldo == Decimal("0.00")


def test_cobro_con_retenciones_excede_cuota_falla() -> None:
    cliente = _cliente()
    clientes = FakeClienteRepository([cliente])
    cuotas = CuotaGenerosa()
    cobro = RegistrarCobro(
        clientes,
        FakeMovimientoRepository(),
        cuotas,
        _adjuntos_nulos(),
        _storage_nulo(),
        FakeClock(),
    )
    cuota_id = cuotas.crear_pendiente(cliente.id, Decimal("60500.00"))
    with pytest.raises(Conflicto):
        cobro.execute(
            RegistrarCobroCommand(
                cliente_id=cliente.id,
                fecha=date(2026, 10, 6),
                monto=Decimal("60000.00"),
                cuota_id=cuota_id,
                retenciones=(_retencion("500"), _retencion("500")),
            )
        )


def test_cobro_sin_cuota_con_retenciones_registra_igual() -> None:
    """La retención queda registrada aunque no impute a cuota (cuenta corriente)."""
    cliente = _cliente()
    clientes = FakeClienteRepository([cliente])
    movimientos = FakeMovimientoRepository()
    cobro = RegistrarCobro(
        clientes, movimientos, CuotaGenerosa(), _adjuntos_nulos(), _storage_nulo(), FakeClock()
    )
    mov = cobro.execute(
        RegistrarCobroCommand(
            cliente_id=cliente.id,
            fecha=date(2026, 10, 6),
            monto=Decimal("1000.00"),
            retenciones=(_retencion(),),
        )
    )
    assert mov.importe_imputado == Decimal("1500.00")
    assert mov.monto == Decimal("1000.00")


# --- Saldos por medio de pago / arqueo (H7) ---------------------------------
def test_saldos_por_medio_y_arqueo() -> None:
    from taller.application.use_cases.reportes import SaldosPorMedio

    repo = FakeMovimientoRepository()
    for monto, medio, signo in [
        ("1000", MedioPago.EFECTIVO, SignoMovimiento.INGRESO),
        ("400", MedioPago.EFECTIVO, SignoMovimiento.EGRESO),
        ("2000", MedioPago.MERCADO_PAGO, SignoMovimiento.INGRESO),
    ]:
        mov = Movimiento(
            fecha=date(2026, 10, 6),
            signo=signo,
            naturaleza=NaturalezaMovimiento.VENTA_TRABAJO,
            monto=Decimal(monto),
            medio=medio,
        )
        mov.comprobar()
        repo.guardar(mov)
    por_medio = {s.medio: s for s in SaldosPorMedio(repo).execute()}
    efectivo = por_medio[MedioPago.EFECTIVO]
    assert efectivo.ingresos == Decimal("1000.00")
    assert efectivo.egresos == Decimal("400.00")
    assert efectivo.saldo == Decimal("600.00")
    assert por_medio[MedioPago.MERCADO_PAGO].saldo == Decimal("2000.00")
    # El arqueo del día es el mismo reporte acotado al día.
    arqueo = SaldosPorMedio(repo).execute(desde=date(2026, 10, 6), hasta=date(2026, 10, 6))
    assert len(arqueo) == 2
    otro_dia = SaldosPorMedio(repo).execute(desde=date(2026, 10, 7), hasta=date(2026, 10, 7))
    assert otro_dia == []


# --- Costo real de repuestos (H6) ------------------------------------------
def test_item_costo_unitario_y_costo_real() -> None:
    from taller.domain.entities.orden_trabajo import ItemOT
    from taller.domain.enums import OrigenPieza, TipoItem

    item = ItemOT(
        descripcion="Pastillas",
        tipo=TipoItem.REPUESTO,
        cantidad=Decimal("2"),
        precio_unitario=Decimal("5000"),
        origen_pieza=OrigenPieza.TALLER,
        costo_unitario=Decimal("3000"),
    )
    assert item.costo_real == Decimal("6000.00")
    sin_costo = ItemOT(
        descripcion="Mano de obra",
        tipo=TipoItem.MANO_OBRA,
        precio_unitario=Decimal("5000"),
    )
    assert sin_costo.costo_real is None
    with pytest.raises(SolicitudInvalida):
        ItemOT(
            descripcion="X",
            tipo=TipoItem.MANO_OBRA,
            costo_unitario=Decimal("-1"),
        )


def test_rentabilidad_incluye_costo_estimado() -> None:
    from taller.adapters.inbound.api.schemas_finanzas import RentabilidadResponse
    from taller.application.use_cases.reportes import RentabilidadOT

    r = RentabilidadOT(
        ot_id=uuid4(),
        presupuestado=Decimal("15000"),
        ingresos=Decimal("15000"),
        costos=Decimal("6000"),
        resultado=Decimal("9000"),
        costo_estimado=Decimal("6000"),
    )
    respuesta = RentabilidadResponse.desde(r)
    assert respuesta.costo_estimado == Decimal("6000.00")


# --- Retenciones al pagar (SICORE/IIBB) -------------------------------------
def test_pago_compra_con_retencion_salda_compra() -> None:
    from taller.domain.entities.compra import Compra, CompraItem
    from taller.domain.enums import CondicionPago
    from taller.domain.value_objects.cuit import Cuit

    proveedor = Proveedor(razon_social="Repuestos SA", cuit=Cuit("30712345678"))
    compras = FakeCompraRepository()
    compra = Compra(
        proveedor_id=proveedor.id,
        fecha=date(2026, 10, 1),
        condicion_pago=CondicionPago.CONTADO,
        items=[
            CompraItem(
                descripcion="Filtro", cantidad=Decimal("1"),
                precio_unitario=Decimal("1000"), alicuota_iva=Decimal("21"),
            )
        ],
    )
    compras.guardar(compra)
    cuotas = FakeCuotaRepository()
    for c in generar_cuotas(
        origen=OrigenCuota.PAGO,
        referencia_tipo="compra",
        referencia_id=compra.id,
        periodicidad=Periodicidad.UNICA,
        cantidad=1,
        primer_vencimiento=date(2026, 10, 10),
        monto_total=compra.total,
        proveedor_id=proveedor.id,
    ):
        cuotas.guardar(c)
    retencion = Retencion(tipo=RetencionTipo.IIBB, monto=Decimal("205.00"), certificado="68-1")
    compra = RegistrarPagoCompra(compras, cuotas, FakeMovimientoRepository()).execute(
        RegistrarPagoCompraCommand(
            compra_id=compra.id,
            fecha=date(2026, 10, 6),
            monto=Decimal("1005.00"),  # 1210 total − 205 retención
            retenciones=(retencion,),
        )
    )
    assert compra.estado == EstadoCompra.PAGADA
    cuota = [c for c in cuotas.listar(referencia_id=compra.id)][0]
    assert cuota.saldo == Decimal("0.00")


def test_pago_compra_retencion_excede_saldo_falla() -> None:
    from taller.domain.entities.compra import Compra, CompraItem
    from taller.domain.enums import CondicionPago
    from taller.domain.value_objects.cuit import Cuit

    proveedor = Proveedor(razon_social="Repuestos SA", cuit=Cuit("30712345678"))
    compras = FakeCompraRepository()
    compra = Compra(
        proveedor_id=proveedor.id,
        fecha=date(2026, 10, 1),
        condicion_pago=CondicionPago.CONTADO,
        items=[
            CompraItem(
                descripcion="Filtro", cantidad=Decimal("1"),
                precio_unitario=Decimal("1000"), alicuota_iva=Decimal("21"),
            )
        ],
    )
    compras.guardar(compra)
    cuotas = FakeCuotaRepository()
    for c in generar_cuotas(
        origen=OrigenCuota.PAGO,
        referencia_tipo="compra",
        referencia_id=compra.id,
        periodicidad=Periodicidad.UNICA,
        cantidad=1,
        primer_vencimiento=date(2026, 10, 10),
        monto_total=compra.total,
        proveedor_id=proveedor.id,
    ):
        cuotas.guardar(c)
    retencion = Retencion(tipo=RetencionTipo.IIBB, monto=Decimal("300.00"))
    with pytest.raises(Conflicto):
        RegistrarPagoCompra(compras, cuotas, FakeMovimientoRepository()).execute(
            RegistrarPagoCompraCommand(
                compra_id=compra.id,
                fecha=date(2026, 10, 6),
                monto=Decimal("1000.00"),  # 1000 + 300 > 1210
                retenciones=(retencion,),
            )
        )


def test_retencion_caja_no_quebra_saldo_por_medio() -> None:
    """El saldo por medio (H7) usa el efectivo: la retención no infla la caja."""
    from taller.application.use_cases.reportes import SaldosPorMedio

    repo = FakeMovimientoRepository()
    mov = Movimiento(
        fecha=date(2026, 10, 6),
        signo=SignoMovimiento.EGRESO,
        naturaleza=NaturalezaMovimiento.PAGO_PROVEEDOR,
        monto=Decimal("1005.00"),
        medio=MedioPago.TRANSFERENCIA,
        retenciones=[Retencion(tipo=RetencionTipo.IIBB, monto=Decimal("205.00"))],
    )
    mov.comprobar()
    repo.guardar(mov)
    saldo = [s for s in SaldosPorMedio(repo).execute() if s.medio is MedioPago.TRANSFERENCIA][0]
    assert saldo.egresos == Decimal("1005.00")   # caja real
    assert mov.importe_imputado == Decimal("1210.00")  # lo que cubre la compra


# --- Fakes mínimos de este módulo ------------------------------------------
class CuotaGenerosa(FakeCuotaRepository):
    """Cuota generosa permite probar el flujo de retenciones contra cuota."""

    def crear_pendiente(self, cliente_id, monto):

        cuota = Cuota(
            origen=OrigenCuota.COBRO,
            referencia_tipo="comprobante",
            referencia_id=uuid4(),
            numero=1,
            fecha_vencimiento=date(2026, 10, 10),
            monto=monto,
            cliente_id=cliente_id,
        )
        self.guardar(cuota)
        return cuota.id


def _adjuntos_nulos():
    class _A:
        def guardar(self, adjunto):
            return adjunto

        def listar(self, movimiento_id):
            return []

    return _A()


def _storage_nulo():
    class _S:
        def guardar(self, *, nombre_original, contenido, content_type):
            return f"var/{nombre_original}"

    return _S()

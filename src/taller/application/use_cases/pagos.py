from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from taller.application.use_cases.efectivo import comprobar_efectivo
from taller.domain.entities.movimiento import Movimiento
from taller.domain.entities.pagos import Adelanto, Liquidacion
from taller.domain.enums import (
    EstadoAdelanto,
    EstadoMovimiento,
    MedioPago,
    NaturalezaMovimiento,
    SignoMovimiento,
    TipoRemuneracion,
)
from taller.domain.exceptions import Conflicto, NoEncontrado, SolicitudInvalida
from taller.domain.ports import Clock
from taller.domain.ports.finanzas import MovimientoRepository
from taller.domain.ports.pagos import AdelantoRepository, LiquidacionRepository
from taller.domain.ports.repositories import TrabajadorRepository

_CERO = Decimal("0.00")
_CENTAVOS = Decimal("0.01")


def _validar_trabajador(trabajadores: TrabajadorRepository, trabajador_id: UUID) -> None:
    if trabajadores.obtener(trabajador_id) is None:
        raise NoEncontrado("El trabajador indicado no existe")


@dataclass(frozen=True, slots=True)
class RegistrarAdelantoCommand:
    trabajador_id: UUID
    fecha: date
    monto: Decimal
    motivo: str | None = None
    medio: MedioPago = MedioPago.EFECTIVO


class RegistrarAdelanto:
    """Adelanto a un trabajador: genera el pago y queda pendiente de descontar (RN-116)."""

    def __init__(
        self,
        trabajadores: TrabajadorRepository,
        adelantos: AdelantoRepository,
        movimientos: MovimientoRepository,
        clock: Clock,
    ) -> None:
        self._trabajadores = trabajadores
        self._adelantos = adelantos
        self._movimientos = movimientos
        self._clock = clock

    def execute(self, cmd: RegistrarAdelantoCommand) -> Adelanto:
        _validar_trabajador(self._trabajadores, cmd.trabajador_id)
        movimiento = Movimiento(
            fecha=cmd.fecha,
            signo=SignoMovimiento.EGRESO,
            naturaleza=NaturalezaMovimiento.PAGO_TRABAJADOR,
            monto=cmd.monto,
            medio=cmd.medio,
            trabajador_id=cmd.trabajador_id,
            observaciones=cmd.motivo or "Adelanto",
            creado_en=self._clock.ahora(),
        )
        comprobar_efectivo(movimiento)
        self._movimientos.guardar(movimiento)
        adelanto = Adelanto(
            trabajador_id=cmd.trabajador_id,
            fecha=cmd.fecha,
            monto=cmd.monto,
            motivo=cmd.motivo,
            movimiento_id=movimiento.id,
            creado_en=self._clock.ahora(),
        )
        self._adelantos.guardar(adelanto)
        return adelanto


class AnularAdelanto:
    def __init__(self, adelantos: AdelantoRepository) -> None:
        self._adelantos = adelantos

    def execute(self, adelanto_id: UUID) -> Adelanto:
        adelanto = self._adelantos.obtener(adelanto_id)
        if adelanto is None:
            raise NoEncontrado("Adelanto no encontrado")
        adelanto.anular()
        self._adelantos.guardar(adelanto)
        return adelanto


@dataclass(frozen=True, slots=True)
class LiquidarTrabajadorCommand:
    trabajador_id: UUID
    periodo_desde: date
    periodo_hasta: date
    monto_bruto: Decimal
    fecha_pago: date
    medio: MedioPago = MedioPago.EFECTIVO
    comprobante_id: UUID | None = None
    observaciones: str | None = None


class LiquidarTrabajador:
    """Liquida un período: descuenta adelantos pendientes y genera el pago (RN-115, RN-116)."""

    def __init__(
        self,
        trabajadores: TrabajadorRepository,
        liquidaciones: LiquidacionRepository,
        adelantos: AdelantoRepository,
        movimientos: MovimientoRepository,
        clock: Clock,
    ) -> None:
        self._trabajadores = trabajadores
        self._liquidaciones = liquidaciones
        self._adelantos = adelantos
        self._movimientos = movimientos
        self._clock = clock

    def execute(self, cmd: LiquidarTrabajadorCommand) -> Liquidacion:
        _validar_trabajador(self._trabajadores, cmd.trabajador_id)
        pendientes = self._adelantos.listar(
            trabajador_id=cmd.trabajador_id, estado=EstadoAdelanto.PENDIENTE
        )
        descontados = sum((a.monto for a in pendientes), Decimal("0.00"))
        liquidacion = Liquidacion(
            trabajador_id=cmd.trabajador_id,
            periodo_desde=cmd.periodo_desde,
            periodo_hasta=cmd.periodo_hasta,
            monto_bruto=cmd.monto_bruto,
            adelantos_descontados=descontados,
            observaciones=cmd.observaciones,
            creado_en=self._clock.ahora(),
        )
        if liquidacion.monto_neto <= 0:
            raise Conflicto("El neto de la liquidación debe ser mayor a cero")

        movimiento = Movimiento(
            fecha=cmd.fecha_pago,
            signo=SignoMovimiento.EGRESO,
            naturaleza=NaturalezaMovimiento.PAGO_TRABAJADOR,
            monto=liquidacion.monto_neto,
            medio=cmd.medio,
            trabajador_id=cmd.trabajador_id,
            comprobante_id=cmd.comprobante_id,
            observaciones=cmd.observaciones,
            creado_en=self._clock.ahora(),
        )
        comprobar_efectivo(movimiento)
        self._movimientos.guardar(movimiento)
        liquidacion.pagar(self._clock.ahora(), movimiento.id)
        self._liquidaciones.guardar(liquidacion)
        for adelanto in pendientes:
            adelanto.descontar(liquidacion.id)
            self._adelantos.guardar(adelanto)
        return liquidacion


@dataclass(frozen=True, slots=True)
class SugerenciaLiquidacion:
    tipo_remuneracion: TipoRemuneracion
    monto_bruto: Decimal | None
    horas: Decimal | None = None
    valor_hora: Decimal | None = None
    ganancia_periodo: Decimal | None = None
    porcentaje_comision: Decimal | None = None


class SugerirLiquidacion:
    """Bruto sugerido según la remuneración; el operador lo confirma o corrige.

    - sueldo: el monto fijo del período.
    - jornal: horas trabajadas × valor por hora.
    - comisión: porcentaje de la ganancia del período (ingresos − egresos comprobados),
      sin contar lo pagado a quienes cobran comisión, para no descontarla de sí misma.
    """

    def __init__(
        self, trabajadores: TrabajadorRepository, movimientos: MovimientoRepository
    ) -> None:
        self._trabajadores = trabajadores
        self._movimientos = movimientos

    def execute(
        self, trabajador_id: UUID, desde: date, hasta: date, horas: Decimal | None = None
    ) -> SugerenciaLiquidacion:
        trabajador = self._trabajadores.obtener(trabajador_id)
        if trabajador is None:
            raise NoEncontrado("El trabajador indicado no existe")
        tipo = trabajador.tipo_remuneracion
        if tipo is TipoRemuneracion.SUELDO:
            return SugerenciaLiquidacion(tipo, trabajador.monto_periodo)
        if tipo is TipoRemuneracion.JORNAL:
            if horas is not None and horas < 0:
                raise SolicitudInvalida("Las horas trabajadas no pueden ser negativas")
            bruto = (
                (horas * trabajador.valor_hora).quantize(_CENTAVOS)
                if horas is not None and trabajador.valor_hora is not None
                else None
            )
            return SugerenciaLiquidacion(tipo, bruto, horas=horas, valor_hora=trabajador.valor_hora)
        ganancia = self._ganancia(desde, hasta)
        porcentaje = trabajador.porcentaje_comision
        bruto = (
            (max(ganancia, _CERO) * porcentaje / 100).quantize(_CENTAVOS)
            if porcentaje is not None
            else None
        )
        return SugerenciaLiquidacion(
            tipo, bruto, ganancia_periodo=ganancia, porcentaje_comision=porcentaje
        )

    def _ganancia(self, desde: date, hasta: date) -> Decimal:
        comisionistas = {
            t.id
            for t in self._trabajadores.listar(q=None, incluir_archivados=True)
            if t.tipo_remuneracion is TipoRemuneracion.COMISION
        }
        ganancia = _CERO
        for m in self._movimientos.listar(
            desde=desde, hasta=hasta, estado=EstadoMovimiento.COMPROBADO
        ):
            if m.signo is SignoMovimiento.INGRESO:
                ganancia += m.monto
            elif m.trabajador_id not in comisionistas:
                ganancia -= m.monto
        return ganancia


@dataclass(frozen=True, slots=True)
class RegistrarGastoCommand:
    fecha: date
    monto: Decimal
    medio: MedioPago = MedioPago.EFECTIVO
    rubro_id: UUID | None = None
    tipo_pago_id: UUID | None = None
    observaciones: str | None = None


class RegistrarGasto:
    def __init__(self, movimientos: MovimientoRepository, clock: Clock) -> None:
        self._movimientos = movimientos
        self._clock = clock

    def execute(self, cmd: RegistrarGastoCommand) -> Movimiento:
        movimiento = Movimiento(
            fecha=cmd.fecha,
            signo=SignoMovimiento.EGRESO,
            naturaleza=NaturalezaMovimiento.GASTO_OPERATIVO,
            monto=cmd.monto,
            medio=cmd.medio,
            rubro_id=cmd.rubro_id,
            tipo_pago_id=cmd.tipo_pago_id,
            observaciones=cmd.observaciones,
            creado_en=self._clock.ahora(),
        )
        comprobar_efectivo(movimiento)
        self._movimientos.guardar(movimiento)
        return movimiento


@dataclass(frozen=True, slots=True)
class ListarAdelantosQuery:
    trabajador_id: UUID | None = None
    estado: EstadoAdelanto | None = None


class ListarAdelantos:
    def __init__(self, repo: AdelantoRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarAdelantosQuery) -> list[Adelanto]:
        return self._repo.listar(trabajador_id=query.trabajador_id, estado=query.estado)


class ListarLiquidaciones:
    def __init__(self, repo: LiquidacionRepository) -> None:
        self._repo = repo

    def execute(self, trabajador_id: UUID | None = None) -> list[Liquidacion]:
        return self._repo.listar(trabajador_id=trabajador_id)

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from taller.application.use_cases.pagos import (
    LiquidarTrabajador,
    LiquidarTrabajadorCommand,
    RegistrarGasto,
    RegistrarGastoCommand,
)
from taller.domain.calendario import fecha_argentina, periodos_sueldo, vencimientos_gasto
from taller.domain.entities.notificacion import Notificacion
from taller.domain.entities.usuario import Rol
from taller.domain.entities.vencimiento import DIAS_AVISO_SUELDO, GastoFijo, Obligacion
from taller.domain.enums import (
    EstadoLiquidacion,
    EstadoObligacion,
    MedioPago,
    OrigenObligacion,
    PeriodicidadGasto,
    Severidad,
    TipoNotificacion,
)
from taller.domain.exceptions import EstadoInvalido, NoEncontrado
from taller.domain.ports import Clock
from taller.domain.ports.notificaciones import NotificacionRepository, Notificador
from taller.domain.ports.pagos import LiquidacionRepository
from taller.domain.ports.repositories import TrabajadorRepository
from taller.domain.ports.vencimientos import GastoFijoRepository, ObligacionRepository

REFERENCIA = "obligacion"
ROLES_FINANZAS = (Rol.ADMIN, Rol.ADMINISTRACION)
# Sólo se generan vencimientos de hasta una semana atrás: un gasto cargado con inicio viejo
# no debe inundar el panel con períodos que ya se pagaron por fuera del sistema.
_VENTANA_ATRAS = timedelta(days=7)


def _pesos(monto: Decimal) -> str:
    return "$" + f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# --- Gastos fijos ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GastoFijoCommand:
    concepto: str
    fecha_inicio: date
    periodicidad: PeriodicidadGasto = PeriodicidadGasto.MENSUAL
    dia_vencimiento: int = 10
    fecha_fin: date | None = None
    dias_aviso: int = 3
    monto_estimado: Decimal | None = None
    rubro_id: UUID | None = None
    medio: MedioPago | None = None


def _aplicar(gasto: GastoFijo, cmd: GastoFijoCommand) -> None:
    gasto.concepto = cmd.concepto.strip()
    gasto.fecha_inicio = cmd.fecha_inicio
    gasto.periodicidad = cmd.periodicidad
    gasto.dia_vencimiento = cmd.dia_vencimiento
    gasto.fecha_fin = cmd.fecha_fin
    gasto.dias_aviso = cmd.dias_aviso
    gasto.monto_estimado = cmd.monto_estimado
    gasto.rubro_id = cmd.rubro_id
    gasto.medio = cmd.medio
    gasto.validar()


class ListarGastosFijos:
    def __init__(self, gastos: GastoFijoRepository) -> None:
        self._gastos = gastos

    def execute(self, incluir_archivados: bool = False) -> list[GastoFijo]:
        return self._gastos.listar(incluir_archivados=incluir_archivados)


class CrearGastoFijo:
    def __init__(self, gastos: GastoFijoRepository) -> None:
        self._gastos = gastos

    def execute(self, cmd: GastoFijoCommand) -> GastoFijo:
        gasto = GastoFijo(
            concepto=cmd.concepto.strip(),
            fecha_inicio=cmd.fecha_inicio,
            periodicidad=cmd.periodicidad,
            dia_vencimiento=cmd.dia_vencimiento,
            fecha_fin=cmd.fecha_fin,
            dias_aviso=cmd.dias_aviso,
            monto_estimado=cmd.monto_estimado,
            rubro_id=cmd.rubro_id,
            medio=cmd.medio,
        )
        self._gastos.guardar(gasto)
        return gasto


class ActualizarGastoFijo:
    def __init__(self, gastos: GastoFijoRepository) -> None:
        self._gastos = gastos

    def execute(self, gasto_id: UUID, cmd: GastoFijoCommand) -> GastoFijo:
        gasto = self._gastos.obtener(gasto_id)
        if gasto is None:
            raise NoEncontrado("Gasto fijo no encontrado")
        _aplicar(gasto, cmd)
        self._gastos.guardar(gasto)
        return gasto


class ArchivarGastoFijo:
    """Deja de generar vencimientos; los pendientes que ya existen se omiten aparte."""

    def __init__(self, gastos: GastoFijoRepository, clock: Clock) -> None:
        self._gastos = gastos
        self._clock = clock

    def execute(self, gasto_id: UUID) -> GastoFijo:
        gasto = self._gastos.obtener(gasto_id)
        if gasto is None:
            raise NoEncontrado("Gasto fijo no encontrado")
        gasto.archivar(self._clock.ahora())
        self._gastos.guardar(gasto)
        return gasto


# --- Generación y avisos (job de cumplimiento) --------------------------------


@dataclass(frozen=True, slots=True)
class ResultadoVencimientos:
    generadas: int
    resueltas: int
    avisos: int


class GenerarObligaciones:
    """Crea los vencimientos que entraron en su ventana de aviso. Idempotente.

    Gastos fijos: según periodicidad, día de vencimiento, inicio y fin.
    Sueldos: al cierre de cada período de pago (por jornal no genera). Si el período ya
    se liquidó en Pagos, el vencimiento se da por pagado solo.
    """

    def __init__(
        self,
        gastos: GastoFijoRepository,
        trabajadores: TrabajadorRepository,
        liquidaciones: LiquidacionRepository,
        obligaciones: ObligacionRepository,
        clock: Clock,
    ) -> None:
        self._gastos = gastos
        self._trabajadores = trabajadores
        self._liquidaciones = liquidaciones
        self._obligaciones = obligaciones
        self._clock = clock

    def execute(self) -> tuple[int, int]:
        hoy = fecha_argentina(self._clock.ahora())
        generadas = self._gastos_fijos(hoy) + self._sueldos(hoy)
        return generadas, self._resolver_sueldos_liquidados()

    def _crear(self, obligacion: Obligacion) -> int:
        if self._obligaciones.existe(
            origen=obligacion.origen,
            referencia_id=obligacion.referencia_id,
            fecha_vencimiento=obligacion.fecha_vencimiento,
        ):
            return 0
        self._obligaciones.guardar(obligacion)
        return 1

    def _gastos_fijos(self, hoy: date) -> int:
        creadas = 0
        for gasto in self._gastos.listar():
            fechas = vencimientos_gasto(
                gasto.periodicidad,
                gasto.dia_vencimiento,
                gasto.fecha_inicio,
                gasto.fecha_fin,
                hoy - _VENTANA_ATRAS,
                hoy + timedelta(days=gasto.dias_aviso),
            )
            for vence in fechas:
                creadas += self._crear(
                    Obligacion(
                        origen=OrigenObligacion.GASTO_FIJO,
                        referencia_id=gasto.id,
                        concepto=gasto.concepto,
                        fecha_vencimiento=vence,
                        periodo_desde=vence,
                        periodo_hasta=vence,
                        monto_estimado=gasto.monto_estimado,
                        rubro_id=gasto.rubro_id,
                    )
                )
        return creadas

    def _sueldos(self, hoy: date) -> int:
        creadas = 0
        for trabajador in self._trabajadores.listar(q=None, incluir_archivados=False):
            periodos = periodos_sueldo(
                trabajador.periodicidad_pago,
                hoy - _VENTANA_ATRAS,
                hoy + timedelta(days=DIAS_AVISO_SUELDO),
            )
            for desde, hasta in periodos:
                creadas += self._crear(
                    Obligacion(
                        origen=OrigenObligacion.SUELDO,
                        referencia_id=trabajador.id,
                        concepto=f"Sueldo de {trabajador.nombre}",
                        fecha_vencimiento=hasta,
                        periodo_desde=desde,
                        periodo_hasta=hasta,
                        monto_estimado=trabajador.monto_periodo,
                    )
                )
        return creadas

    def _resolver_sueldos_liquidados(self) -> int:
        resueltas = 0
        for obligacion in self._obligaciones.listar(
            estado=EstadoObligacion.PENDIENTE, origen=OrigenObligacion.SUELDO
        ):
            for liq in self._liquidaciones.listar(trabajador_id=obligacion.referencia_id):
                if liq.estado is not EstadoLiquidacion.PAGADA:
                    continue
                if liq.periodo_desde <= obligacion.periodo_hasta and (
                    liq.periodo_hasta >= obligacion.periodo_desde
                ):
                    obligacion.pagar_con_liquidacion(liq.id, self._clock.ahora())
                    self._obligaciones.guardar(obligacion)
                    resueltas += 1
                    break
        return resueltas


class RecordarVencimientos:
    """Re-lanza el aviso de cada vencimiento pendiente para admin y administración.

    Corre en cada pasada del job (cada `cumplimiento_minutos`): hay un único aviso por
    vencimiento y rol, que vuelve a quedar sin leer y sube arriba de la lista hasta que el
    vencimiento se paga u omite.
    """

    def __init__(
        self,
        obligaciones: ObligacionRepository,
        notificaciones: NotificacionRepository,
        notificador: Notificador,
        clock: Clock,
    ) -> None:
        self._obligaciones = obligaciones
        self._notificaciones = notificaciones
        self._notificador = notificador
        self._clock = clock

    def execute(self) -> int:
        ahora = self._clock.ahora()
        hoy = fecha_argentina(ahora)
        avisos = 0
        for obligacion in self._obligaciones.listar(estado=EstadoObligacion.PENDIENTE):
            titulo, mensaje, severidad = self._texto(obligacion, hoy)
            for rol in ROLES_FINANZAS:
                aviso = self._notificaciones.buscar(
                    referencia_tipo=REFERENCIA,
                    referencia_id=obligacion.id,
                    tipo=TipoNotificacion.VENCIMIENTO_PAGO,
                    rol=rol,
                ) or Notificacion(
                    tipo=TipoNotificacion.VENCIMIENTO_PAGO,
                    titulo=titulo,
                    mensaje=mensaje,
                    referencia_tipo=REFERENCIA,
                    referencia_id=obligacion.id,
                    rol_destino=rol,
                )
                aviso.titulo = titulo
                aviso.mensaje = mensaje
                aviso.severidad = severidad
                aviso.leida = False
                aviso.creada_en = ahora
                self._notificador.notificar(aviso)
                avisos += 1
        return avisos

    @staticmethod
    def _texto(obligacion: Obligacion, hoy: date) -> tuple[str, str, Severidad]:
        vence = obligacion.fecha_vencimiento.strftime("%d/%m/%Y")
        dias = (obligacion.fecha_vencimiento - hoy).days
        if dias < 0:
            cuando = f"Venció el {vence} (hace {-dias} día{'s' if dias != -1 else ''})"
            severidad = Severidad.CRITICA
        elif dias == 0:
            cuando, severidad = "Vence hoy", Severidad.CRITICA
        else:
            cuando = f"Vence el {vence} (en {dias} día{'s' if dias != 1 else ''})"
            severidad = Severidad.ADVERTENCIA
        estimado = (
            f" · estimado {_pesos(obligacion.monto_estimado)}"
            if obligacion.monto_estimado is not None
            else ""
        )
        mensaje = f"{cuando}{estimado}. Entrá a Vencimientos para registrar el pago."
        return f"Pagar: {obligacion.concepto}", mensaje, severidad


class EjecutarVencimientos:
    """Una pasada del job: genera, auto-resuelve y re-lanza avisos."""

    def __init__(self, generar: GenerarObligaciones, recordar: RecordarVencimientos) -> None:
        self._generar = generar
        self._recordar = recordar

    def execute(self) -> ResultadoVencimientos:
        generadas, resueltas = self._generar.execute()
        return ResultadoVencimientos(
            generadas=generadas, resueltas=resueltas, avisos=self._recordar.execute()
        )


# --- Resolución ----------------------------------------------------------------


class ListarObligaciones:
    def __init__(self, obligaciones: ObligacionRepository) -> None:
        self._obligaciones = obligaciones

    def execute(self, estado: EstadoObligacion | None = None) -> list[Obligacion]:
        items = self._obligaciones.listar(estado=estado)
        return sorted(items, key=lambda o: (o.fecha_vencimiento, o.concepto))


def _pendiente(obligaciones: ObligacionRepository, obligacion_id: UUID) -> Obligacion:
    obligacion = obligaciones.obtener(obligacion_id)
    if obligacion is None:
        raise NoEncontrado("Vencimiento no encontrado")
    if not obligacion.pendiente:
        raise EstadoInvalido("El vencimiento ya fue resuelto")
    return obligacion


@dataclass(frozen=True, slots=True)
class PagarGastoFijoCommand:
    monto: Decimal
    fecha: date
    medio: MedioPago = MedioPago.EFECTIVO
    observaciones: str | None = None


class PagarGastoFijo:
    """Registra el gasto operativo con el monto real y cierra el vencimiento."""

    def __init__(
        self,
        obligaciones: ObligacionRepository,
        registrar: RegistrarGasto,
        notificaciones: NotificacionRepository,
        clock: Clock,
    ) -> None:
        self._obligaciones = obligaciones
        self._registrar = registrar
        self._notificaciones = notificaciones
        self._clock = clock

    def execute(self, obligacion_id: UUID, cmd: PagarGastoFijoCommand) -> Obligacion:
        obligacion = _pendiente(self._obligaciones, obligacion_id)
        if obligacion.origen is not OrigenObligacion.GASTO_FIJO:
            raise EstadoInvalido("Los sueldos se pagan liquidando al trabajador")
        movimiento = self._registrar.execute(
            RegistrarGastoCommand(
                fecha=cmd.fecha,
                monto=cmd.monto,
                medio=cmd.medio,
                rubro_id=obligacion.rubro_id,
                observaciones=cmd.observaciones or obligacion.concepto,
            )
        )
        obligacion.pagar_con_movimiento(movimiento.id, self._clock.ahora())
        self._obligaciones.guardar(obligacion)
        self._notificaciones.marcar_leidas_por_referencia(
            referencia_tipo=REFERENCIA, referencia_id=obligacion.id
        )
        return obligacion


@dataclass(frozen=True, slots=True)
class LiquidarSueldoCommand:
    monto_bruto: Decimal
    fecha_pago: date
    medio: MedioPago = MedioPago.EFECTIVO
    observaciones: str | None = None


class LiquidarSueldo:
    """Liquida el período del vencimiento (descuenta adelantos) y lo cierra."""

    def __init__(
        self,
        obligaciones: ObligacionRepository,
        liquidar: LiquidarTrabajador,
        notificaciones: NotificacionRepository,
        clock: Clock,
    ) -> None:
        self._obligaciones = obligaciones
        self._liquidar = liquidar
        self._notificaciones = notificaciones
        self._clock = clock

    def execute(self, obligacion_id: UUID, cmd: LiquidarSueldoCommand) -> Obligacion:
        obligacion = _pendiente(self._obligaciones, obligacion_id)
        if obligacion.origen is not OrigenObligacion.SUELDO:
            raise EstadoInvalido("Este vencimiento no es un sueldo")
        liquidacion = self._liquidar.execute(
            LiquidarTrabajadorCommand(
                trabajador_id=obligacion.referencia_id,
                periodo_desde=obligacion.periodo_desde,
                periodo_hasta=obligacion.periodo_hasta,
                monto_bruto=cmd.monto_bruto,
                fecha_pago=cmd.fecha_pago,
                medio=cmd.medio,
                observaciones=cmd.observaciones,
            )
        )
        obligacion.pagar_con_liquidacion(liquidacion.id, self._clock.ahora())
        self._obligaciones.guardar(obligacion)
        self._notificaciones.marcar_leidas_por_referencia(
            referencia_tipo=REFERENCIA, referencia_id=obligacion.id
        )
        return obligacion


class OmitirObligacion:
    def __init__(
        self,
        obligaciones: ObligacionRepository,
        notificaciones: NotificacionRepository,
        clock: Clock,
    ) -> None:
        self._obligaciones = obligaciones
        self._notificaciones = notificaciones
        self._clock = clock

    def execute(self, obligacion_id: UUID, motivo: str) -> Obligacion:
        obligacion = _pendiente(self._obligaciones, obligacion_id)
        obligacion.omitir(motivo, self._clock.ahora())
        self._obligaciones.guardar(obligacion)
        self._notificaciones.marcar_leidas_por_referencia(
            referencia_tipo=REFERENCIA, referencia_id=obligacion.id
        )
        return obligacion

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from taller.application.use_cases.cobranza_ot import CobranzaOT
from taller.application.use_cases.notificar_ot import NotificacionesOT
from taller.domain.entities.orden_trabajo import Evidencia, ItemOT, OrdenTrabajo, Participacion
from taller.domain.enums import (
    EstadoItem,
    EstadoOT,
    MomentoEvidencia,
    OrigenPieza,
    Prioridad,
    TipoEvidencia,
    TipoItem,
)
from taller.domain.exceptions import (
    ArchivoInvalido,
    Conflicto,
    EstadoInvalido,
    KmInvalido,
    NoEncontrado,
    SinPermiso,
)
from taller.domain.ports import Clock
from taller.domain.ports.notificaciones import Notificador
from taller.domain.ports.ordenes import OrdenTrabajoRepository
from taller.domain.ports.repositories import (
    ClienteRepository,
    TrabajadorRepository,
    VehiculoRepository,
)
from taller.domain.ports.storage import ArchivoStorage


def _resumen_para_aviso(ot: OrdenTrabajo) -> str:
    """Texto breve que identifica la OT en los avisos (siempre presente)."""
    return (ot.motivo_ingreso or "sin detalle").strip()[:40]


def _obtener(repo: OrdenTrabajoRepository, ot_id: UUID) -> OrdenTrabajo:
    ot = repo.obtener(ot_id)
    if ot is None:
        raise NoEncontrado("Orden de trabajo no encontrada")
    return ot


# --- Abrir OT ---------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class AbrirOTCommand:
    vehiculo_id: UUID
    km_ingreso: int
    motivo_ingreso: str
    prioridad: Prioridad = Prioridad.MEDIA
    fecha_estimada: datetime | None = None
    forzar: bool = False


class AbrirOT:
    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        vehiculos: VehiculoRepository,
        clientes: ClienteRepository,
        clock: Clock,
        notificador: Notificador | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._vehiculos = vehiculos
        self._clientes = clientes
        self._clock = clock
        self._notificador = notificador
        self._avisos = NotificacionesOT(notificador, clock=clock)

    def execute(self, cmd: AbrirOTCommand) -> OrdenTrabajo:
        vehiculo = self._vehiculos.obtener(cmd.vehiculo_id)
        if vehiculo is None:
            raise NoEncontrado("Vehículo no encontrado")
        if cmd.km_ingreso < vehiculo.km_actual:
            raise KmInvalido("El km de ingreso no puede ser menor al último registrado")
        # RN-011: una sola OT en curso por vehículo (se permite forzar desde la UI).
        en_curso = [o for o in self._ordenes.listar(vehiculo_id=vehiculo.id) if not o.es_final]
        if en_curso and not cmd.forzar:
            raise Conflicto(
                f"El vehículo {vehiculo.patente} ya tiene una OT en curso",
                details={"ordenes_en_curso": [str(o.id) for o in en_curso]},
            )
        cliente = self._clientes.obtener(vehiculo.cliente_id)
        ot = OrdenTrabajo(
            vehiculo_id=vehiculo.id,
            cliente_id=vehiculo.cliente_id,
            numero=self._ordenes.siguiente_numero(),
            empresa_id=cliente.empresa_id if cliente is not None else None,
            prioridad=cmd.prioridad,
            fecha_ingreso=self._clock.ahora(),
            fecha_estimada=cmd.fecha_estimada,
            km_ingreso=cmd.km_ingreso,
            motivo_ingreso=cmd.motivo_ingreso.strip(),
        )
        self._ordenes.guardar(ot)
        self._avisos.nueva(ot, str(vehiculo.patente))
        return ot


# --- Revisión / diagnóstico -------------------------------------------------
@dataclass(frozen=True, slots=True)
class RegistrarRevisionCommand:
    ot_id: UUID
    diagnostico: str


class RegistrarRevision:
    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, cmd: RegistrarRevisionCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.diagnostico = cmd.diagnostico.strip()
        if ot.estado == EstadoOT.INICIADO:
            ot.iniciar_revision()
        self._ordenes.guardar(ot)
        return ot


# --- Operaciones (ítems) ----------------------------------------------------
@dataclass(frozen=True, slots=True)
class AgregarItemCommand:
    ot_id: UUID
    descripcion: str
    tipo: TipoItem
    cantidad: Decimal = Decimal("1")
    precio_unitario: Decimal = Decimal("0")
    descuento: Decimal = Decimal("0")
    origen_pieza: OrigenPieza | None = None
    mecanico_id: UUID | None = None
    notas: str | None = None
    costo_unitario: Decimal | None = None


class AgregarItem:
    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, cmd: AgregarItemCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        item = ItemOT(
            descripcion=cmd.descripcion,
            tipo=cmd.tipo,
            cantidad=cmd.cantidad,
            precio_unitario=cmd.precio_unitario,
            descuento=cmd.descuento,
            origen_pieza=cmd.origen_pieza,
            mecanico_id=cmd.mecanico_id,
            notas=cmd.notas,
            costo_unitario=cmd.costo_unitario,
        )
        ot.agregar_item(item)
        self._ordenes.guardar(ot)
        return ot


@dataclass(frozen=True, slots=True)
class EditarItemCommand:
    ot_id: UUID
    item_id: UUID
    descripcion: str
    tipo: TipoItem
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal
    origen_pieza: OrigenPieza | None = None
    mecanico_id: UUID | None = None
    notas: str | None = None
    costo_unitario: Decimal | None = None
    # Sin importes (vista del mecánico, RN-106): se conservan precio, descuento y costo.
    con_importes: bool = True


class EditarItem:
    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, cmd: EditarItemCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        actual = ot.buscar_item(cmd.item_id)
        nuevo = ItemOT(
            id=actual.id,
            descripcion=cmd.descripcion,
            tipo=cmd.tipo,
            cantidad=cmd.cantidad,
            precio_unitario=cmd.precio_unitario if cmd.con_importes else actual.precio_unitario,
            descuento=cmd.descuento if cmd.con_importes else actual.descuento,
            estado=actual.estado,
            origen_pieza=cmd.origen_pieza,
            mecanico_id=cmd.mecanico_id,
            notas=(cmd.notas or "").strip() or None,
            motivo_no_realizado=actual.motivo_no_realizado,
            costo_unitario=cmd.costo_unitario if cmd.con_importes else actual.costo_unitario,
        )
        if nuevo.subtotal != actual.subtotal and not ot.precios_editables:
            raise EstadoInvalido("No se pueden editar precios aprobados")
        ot.reemplazar_item(nuevo)
        self._ordenes.guardar(ot)
        return ot


@dataclass(frozen=True, slots=True)
class QuitarItemCommand:
    ot_id: UUID
    item_id: UUID
    con_importes: bool = True


class QuitarItem:
    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, cmd: QuitarItemCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        if not cmd.con_importes and ot.buscar_item(cmd.item_id).tiene_precio:
            raise SinPermiso("Una operación con precio sólo la quita quien maneja los importes")
        ot.quitar_item(cmd.item_id)
        self._ordenes.guardar(ot)
        return ot


@dataclass(frozen=True, slots=True)
class AsignarResponsableCommand:
    ot_id: UUID
    item_id: UUID
    mecanico_id: UUID


class AsignarResponsable:
    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        avisos: NotificacionesOT | None = None,
        trabajadores: TrabajadorRepository | None = None,
        vehiculos: VehiculoRepository | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._avisos = avisos
        self._trabajadores = trabajadores
        self._vehiculos = vehiculos

    def execute(self, cmd: AsignarResponsableCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.asignar_responsable(cmd.item_id, cmd.mecanico_id)
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            responsable = "—"
            if self._trabajadores is not None:
                t = self._trabajadores.obtener(cmd.mecanico_id)
                responsable = t.nombre if t is not None else "—"
            # Sin repos de vehículos a mano: el motivo identifica la OT.
            self._avisos.asignada(ot, _resumen_para_aviso(ot), responsable)
        return ot


@dataclass(frozen=True, slots=True)
class CambiarEstadoItemCommand:
    ot_id: UUID
    item_id: UUID
    accion: EstadoItem
    motivo: str | None = None


class CambiarEstadoItem:
    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        avisos: NotificacionesOT | None = None,
        trabajadores: TrabajadorRepository | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._avisos = avisos
        self._trabajadores = trabajadores

    def execute(self, cmd: CambiarEstadoItemCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        item = ot.buscar_item(cmd.item_id)
        antes = item.estado
        if cmd.accion == EstadoItem.EN_PROCESO:
            item.marcar_en_proceso()
        elif cmd.accion == EstadoItem.COMPLETADO:
            item.completar()
        elif cmd.accion == EstadoItem.NO_REALIZADO:
            item.marcar_no_realizado(cmd.motivo or "")
        else:
            raise EstadoInvalido("Acción de operación no soportada")
        self._ordenes.guardar(ot)
        # «Ya están trabajando sobre el auto»: arranca la primera operación.
        if (
            antes is EstadoItem.PENDIENTE
            and item.estado is EstadoItem.EN_PROCESO
            and self._avisos is not None
            and self._avisos.activo
        ):
            mecanico = "el mecánico"
            if self._trabajadores is not None and item.mecanico_id is not None:
                t = self._trabajadores.obtener(item.mecanico_id)
                mecanico = t.nombre if t is not None else mecanico
            self._avisos.trabajando(ot, _resumen_para_aviso(ot), mecanico)
        return ot


# --- Presupuesto y aprobación ----------------------------------------------
@dataclass(frozen=True, slots=True)
class PresupuestarCommand:
    ot_id: UUID
    vigente_hasta: date | None = None


class Presupuestar:
    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        avisos: NotificacionesOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._avisos = avisos

    def execute(self, cmd: PresupuestarCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.presupuestar(cmd.vigente_hasta)
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.estado(ot, _resumen_para_aviso(ot))
        return ot


@dataclass(frozen=True, slots=True)
class RegistrarAprobacionCommand:
    ot_id: UUID
    actor_id: UUID
    canal: str


class RegistrarAprobacion:
    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        clock: Clock,
        avisos: NotificacionesOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._clock = clock
        self._avisos = avisos

    def execute(self, cmd: RegistrarAprobacionCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.registrar_aprobacion(cmd.actor_id, cmd.canal, self._clock.ahora())
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.estado(ot, _resumen_para_aviso(ot))
        return ot


@dataclass(frozen=True, slots=True)
class RechazarPresupuestoCommand:
    ot_id: UUID


class RechazarPresupuesto:
    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        avisos: NotificacionesOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._avisos = avisos

    def execute(self, cmd: RechazarPresupuestoCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.rechazar()
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.estado(ot, _resumen_para_aviso(ot))
        return ot


# --- Participación y notas --------------------------------------------------
@dataclass(frozen=True, slots=True)
class RegistrarParticipacionCommand:
    ot_id: UUID
    mecanico_id: UUID
    desde: datetime | None = None
    hasta: datetime | None = None
    horas: Decimal | None = None
    notas: str | None = None


class RegistrarParticipacion:
    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, cmd: RegistrarParticipacionCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.registrar_participacion(
            Participacion(
                mecanico_id=cmd.mecanico_id,
                desde=cmd.desde,
                hasta=cmd.hasta,
                horas=cmd.horas,
                notas=cmd.notas,
            )
        )
        self._ordenes.guardar(ot)
        return ot


@dataclass(frozen=True, slots=True)
class AgregarNotaOTCommand:
    ot_id: UUID
    nota: str


class AgregarNotaOT:
    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, cmd: AgregarNotaOTCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.observaciones = cmd.nota.strip()
        self._ordenes.guardar(ot)
        return ot


@dataclass(frozen=True, slots=True)
class AgregarNotaItemCommand:
    ot_id: UUID
    item_id: UUID
    nota: str


class AgregarNotaItem:
    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, cmd: AgregarNotaItemCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        item = ot.buscar_item(cmd.item_id)
        item.notas = cmd.nota.strip()
        self._ordenes.guardar(ot)
        return ot


# --- Validación de cierre / cancelación / reapertura -----------------------
@dataclass(frozen=True, slots=True)
class ValidarCierreCommand:
    ot_id: UUID
    actor_id: UUID
    nota: str | None = None


class ValidarCierre:
    """Cierre técnico: UNA sola validación, no bloqueante (RN-096, RN-105)."""

    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        clock: Clock,
        avisos: NotificacionesOT | None = None,
        cobranza: CobranzaOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._clock = clock
        self._avisos = avisos
        self._cobranza = cobranza

    def execute(self, cmd: ValidarCierreCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.validar_cierre(cmd.actor_id, self._clock.ahora(), cmd.nota)
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.estado(ot, _resumen_para_aviso(ot))
        if self._cobranza is not None:
            self._cobranza.abrir_cuenta(ot)
        return ot


@dataclass(frozen=True, slots=True)
class CancelarOTCommand:
    ot_id: UUID
    motivo: str | None = None


class CancelarOT:
    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        avisos: NotificacionesOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._avisos = avisos

    def execute(self, cmd: CancelarOTCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.cancelar()
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.estado(ot, _resumen_para_aviso(ot))
        return ot


@dataclass(frozen=True, slots=True)
class ReabrirOTCommand:
    ot_id: UUID


class ReabrirOT:
    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        avisos: NotificacionesOT | None = None,
        cobranza: CobranzaOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._avisos = avisos
        self._cobranza = cobranza

    def execute(self, cmd: ReabrirOTCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.reabrir()
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.estado(ot, _resumen_para_aviso(ot))
        if self._cobranza is not None:
            self._cobranza.abrir_cuenta(ot)
        return ot


# --- Evidencia --------------------------------------------------------------
_TIPOS_PERMITIDOS = frozenset(
    {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/quicktime"}
)
_MAX_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class MarcarCobradaCommand:
    ot_id: UUID


class MarcarCobrada:
    """`pendiente_pago → cobrado`: la plata entró (coordinar con el cobro real)."""

    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        avisos: NotificacionesOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._avisos = avisos

    def execute(self, cmd: MarcarCobradaCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.marcar_cobrado()
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.cobrada(ot, _resumen_para_aviso(ot))
        return ot


@dataclass(frozen=True, slots=True)
class EntregarCommand:
    ot_id: UUID


class Entregar:
    """`cobrado → entregado`: el auto vuelve con el cliente."""

    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        avisos: NotificacionesOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._avisos = avisos

    def execute(self, cmd: EntregarCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.entregar()
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.estado(ot, _resumen_para_aviso(ot))
        return ot


@dataclass(frozen=True, slots=True)
class CerrarOrdenCommand:
    ot_id: UUID


class CerrarOrden:
    """`entregado → cerrada`: hoja final (solo admin)."""

    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        clock: Clock,
        avisos: NotificacionesOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._clock = clock
        self._avisos = avisos

    def execute(self, cmd: CerrarOrdenCommand) -> OrdenTrabajo:
        ot = _obtener(self._ordenes, cmd.ot_id)
        ot.cerrar(self._clock.ahora())
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.estado(ot, _resumen_para_aviso(ot))
        return ot


@dataclass(frozen=True, slots=True)
class SubirEvidenciaCommand:
    ot_id: UUID
    autor_id: UUID
    tipo: TipoEvidencia
    momento: MomentoEvidencia
    nombre_original: str
    contenido: bytes
    content_type: str
    item_id: UUID | None = None
    nota: str | None = None


class SubirEvidencia:
    def __init__(
        self, ordenes: OrdenTrabajoRepository, storage: ArchivoStorage, clock: Clock
    ) -> None:
        self._ordenes = ordenes
        self._storage = storage
        self._clock = clock

    def execute(self, cmd: SubirEvidenciaCommand) -> OrdenTrabajo:
        if cmd.content_type not in _TIPOS_PERMITIDOS:
            raise ArchivoInvalido(f"Tipo de archivo no permitido: {cmd.content_type}")
        if len(cmd.contenido) > _MAX_BYTES:
            raise ArchivoInvalido("El archivo supera el tamaño máximo permitido")
        ot = _obtener(self._ordenes, cmd.ot_id)
        if cmd.item_id is not None:
            ot.buscar_item(cmd.item_id)  # valida que la operación exista
        path = self._storage.guardar(
            nombre_original=cmd.nombre_original,
            contenido=cmd.contenido,
            content_type=cmd.content_type,
        )
        ot.agregar_evidencia(
            Evidencia(
                tipo=cmd.tipo,
                momento=cmd.momento,
                archivo_path=path,
                nombre_original=cmd.nombre_original,
                autor_id=cmd.autor_id,
                item_id=cmd.item_id,
                nota=cmd.nota,
                creada_en=self._clock.ahora(),
                content_type=cmd.content_type,
            )
        )
        self._ordenes.guardar(ot)
        return ot


# --- Consultas --------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ListarOTQuery:
    estado: EstadoOT | None = None
    cliente_id: UUID | None = None
    vehiculo_id: UUID | None = None
    mecanico_id: UUID | None = None
    del_dia: date | None = None


class ListarOT:
    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, query: ListarOTQuery) -> list[OrdenTrabajo]:
        return self._ordenes.listar(
            estado=query.estado,
            cliente_id=query.cliente_id,
            vehiculo_id=query.vehiculo_id,
            mecanico_id=query.mecanico_id,
            del_dia=query.del_dia,
        )


class ObtenerOT:
    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, ot_id: UUID) -> OrdenTrabajo:
        return _obtener(self._ordenes, ot_id)


@dataclass(frozen=True, slots=True)
class AgendaDelDiaQuery:
    mecanico_id: UUID | None = None
    dia: date | None = None


class AgendaDelDia:
    """OT del día y/o asignadas a un mecánico (RN-099)."""

    def __init__(self, ordenes: OrdenTrabajoRepository) -> None:
        self._ordenes = ordenes

    def execute(self, query: AgendaDelDiaQuery) -> list[OrdenTrabajo]:
        return self._ordenes.listar(mecanico_id=query.mecanico_id, del_dia=query.dia)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from taller.domain.enums import (
    EstadoItem,
    EstadoOT,
    MomentoEvidencia,
    OrigenPieza,
    Prioridad,
    TipoEvidencia,
    TipoItem,
)
from taller.domain.exceptions import EstadoInvalido, OTCerrada, SolicitudInvalida

_DOS_DECIMALES = Decimal("0.01")

_ESTADOS_FINALES = frozenset({EstadoOT.CERRADA, EstadoOT.CANCELADA})
_ESTADOS_PRECIO_EDITABLE = frozenset(
    {EstadoOT.INICIADO, EstadoOT.REVISION, EstadoOT.PRESUPUESTADO, EstadoOT.RECHAZADO}
)

_TRANSICIONES: dict[EstadoOT, frozenset[EstadoOT]] = {
    EstadoOT.INICIADO: frozenset({EstadoOT.REVISION, EstadoOT.CANCELADA}),
    EstadoOT.REVISION: frozenset({EstadoOT.PRESUPUESTADO, EstadoOT.CANCELADA}),
    EstadoOT.PRESUPUESTADO: frozenset({EstadoOT.EN_TALLER, EstadoOT.RECHAZADO}),
    EstadoOT.RECHAZADO: frozenset({EstadoOT.PRESUPUESTADO, EstadoOT.CANCELADA}),
    EstadoOT.EN_TALLER: frozenset({EstadoOT.PENDIENTE_PAGO, EstadoOT.PRESUPUESTADO}),
    EstadoOT.PENDIENTE_PAGO: frozenset({EstadoOT.COBRADO, EstadoOT.EN_TALLER}),
    EstadoOT.COBRADO: frozenset({EstadoOT.ENTREGADO}),
    EstadoOT.ENTREGADO: frozenset({EstadoOT.CERRADA}),
    EstadoOT.CERRADA: frozenset({EstadoOT.PENDIENTE_PAGO}),  # reapertura (admin, en el caso de uso)
    EstadoOT.CANCELADA: frozenset(),
}


@dataclass(slots=True)
class ItemOT:
    """Operación de la OT. Cada operación tiene un responsable y puede tener notas."""

    descripcion: str
    tipo: TipoItem
    id: UUID = field(default_factory=uuid4)
    cantidad: Decimal = Decimal("1")
    precio_unitario: Decimal = Decimal("0")
    descuento: Decimal = Decimal("0")
    estado: EstadoItem = EstadoItem.PENDIENTE
    origen_pieza: OrigenPieza | None = None
    mecanico_id: UUID | None = None
    notas: str | None = None
    motivo_no_realizado: str | None = None
    # Cuanto le costó al taller la pieza/repuesto (H6): alimenta la rentabilidad
    # real. Lo carga administración/jefe; el mecánico no lo ve (RN-106).
    costo_unitario: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.descripcion.strip():
            raise SolicitudInvalida("La operación necesita una descripción")
        if self.cantidad <= 0:
            raise SolicitudInvalida("La cantidad debe ser mayor a cero")
        if self.precio_unitario < 0 or self.descuento < 0:
            raise SolicitudInvalida("Los importes no pueden ser negativos")
        if self.costo_unitario is not None and self.costo_unitario < 0:
            raise SolicitudInvalida("El costo no puede ser negativo")
        if self.tipo == TipoItem.REPUESTO and self.origen_pieza is None:
            raise SolicitudInvalida("El repuesto debe indicar su origen (taller/cliente)")
        if self.tipo != TipoItem.REPUESTO and self.origen_pieza is not None:
            raise SolicitudInvalida("Solo los repuestos tienen origen de pieza")

    @property
    def subtotal(self) -> Decimal:
        return (self.cantidad * self.precio_unitario - self.descuento).quantize(
            _DOS_DECIMALES, ROUND_HALF_UP
        )

    @property
    def tiene_precio(self) -> bool:
        return self.precio_unitario > 0

    @property
    def costo_real(self) -> Decimal | None:
        """Costo total para el taller (H6): None si el costo no fue cargado."""
        if self.costo_unitario is None:
            return None
        return (self.cantidad * self.costo_unitario).quantize(_DOS_DECIMALES, ROUND_HALF_UP)

    def marcar_en_proceso(self) -> None:
        """En marcha: desde pendiente, para rehacer una completada o retomar una
        marcada no realizada (los mecánicos se equivocan también)."""
        self.estado = EstadoItem.EN_PROCESO
        self.motivo_no_realizado = None

    def completar(self) -> None:
        """Completa directamente (tap-✓ sin pasar por en proceso si ya terminó)."""
        self.estado = EstadoItem.COMPLETADO
        self.motivo_no_realizado = None

    def marcar_no_realizado(self, motivo: str) -> None:
        if not motivo.strip():
            raise SolicitudInvalida("Debe indicar el motivo de la operación no realizada")
        self.estado = EstadoItem.NO_REALIZADO
        self.motivo_no_realizado = motivo.strip()


@dataclass(slots=True)
class Participacion:
    """Mecánico que trabajó en la OT (uno o varios)."""

    mecanico_id: UUID
    id: UUID = field(default_factory=uuid4)
    desde: datetime | None = None
    hasta: datetime | None = None
    horas: Decimal | None = None
    notas: str | None = None


@dataclass(slots=True)
class Evidencia:
    """Foto/video de la OT o de una operación. Se conserva como histórico (RN-084)."""

    tipo: TipoEvidencia
    momento: MomentoEvidencia
    archivo_path: str
    nombre_original: str
    autor_id: UUID
    id: UUID = field(default_factory=uuid4)
    item_id: UUID | None = None
    nota: str | None = None
    creada_en: datetime | None = None
    content_type: str | None = None


@dataclass(slots=True)
class OrdenTrabajo:
    vehiculo_id: UUID
    cliente_id: UUID
    numero: int
    empresa_id: UUID | None = None
    # Patente de referencia (la completa el repositorio; nunca la edita el usario).
    patente: str | None = None
    id: UUID = field(default_factory=uuid4)
    estado: EstadoOT = EstadoOT.INICIADO
    prioridad: Prioridad = Prioridad.MEDIA
    fecha_ingreso: datetime | None = None
    fecha_estimada: datetime | None = None
    fecha_cierre: datetime | None = None
    presupuesto_vigente_hasta: date | None = None
    km_ingreso: int | None = None
    motivo_ingreso: str | None = None
    diagnostico: str | None = None
    observaciones: str | None = None
    aprobado_por: UUID | None = None
    aprobado_canal: str | None = None
    aprobado_en: datetime | None = None
    validado_por: UUID | None = None
    validado_en: datetime | None = None
    validado_nota: str | None = None
    items: list[ItemOT] = field(default_factory=list)
    participaciones: list[Participacion] = field(default_factory=list)
    evidencias: list[Evidencia] = field(default_factory=list)
    version: int = 1

    # --- totales (siempre en el servidor) ----------------------------------
    @property
    def codigo(self) -> str:
        """Identificador humano: OT-{año}{mes}-{número} — letras + info + único.

        El `numero` es la clave única (nunca se reutiliza); el prefijo aporta el
        año/mes de creción para ubicar la orden de un vistazo y ordenarla.
        Ej.: OT-2610-0042 (octubre 2026, la cuadragésima segunda del taller).
        """
        fecha = self.fecha_ingreso
        anio_mes = f"{fecha.year % 100:02d}{fecha.month:02d}" if fecha else "0000"
        return f"OT-{anio_mes}-{self.numero:04d}"

    @property
    def total(self) -> Decimal:
        return sum((i.subtotal for i in self.items), Decimal("0.00")).quantize(_DOS_DECIMALES)

    def _total_por(self, tipo: TipoItem) -> Decimal:
        return sum((i.subtotal for i in self.items if i.tipo == tipo), Decimal("0.00")).quantize(
            _DOS_DECIMALES
        )

    @property
    def total_mano_obra(self) -> Decimal:
        return self._total_por(TipoItem.MANO_OBRA)

    @property
    def total_repuestos(self) -> Decimal:
        return self._total_por(TipoItem.REPUESTO)

    @property
    def total_servicios(self) -> Decimal:
        return self._total_por(TipoItem.SERVICIO)

    # --- edición -----------------------------------------------------------
    @property
    def es_final(self) -> bool:
        return self.estado in _ESTADOS_FINALES

    @property
    def editable(self) -> bool:
        return not self.es_final

    @property
    def precios_editables(self) -> bool:
        return self.estado in _ESTADOS_PRECIO_EDITABLE

    def _exigir_editable(self) -> None:
        if not self.editable:
            raise OTCerrada(f"La OT está {self.estado.value} y no admite cambios")

    def agregar_item(self, item: ItemOT) -> None:
        self._exigir_editable()
        self.items.append(item)

    def buscar_item(self, item_id: UUID) -> ItemOT:
        for item in self.items:
            if item.id == item_id:
                return item
        raise EstadoInvalido("La operación no existe en la OT")

    def quitar_item(self, item_id: UUID) -> None:
        self._exigir_editable()
        item = self.buscar_item(item_id)
        if item.estado != EstadoItem.PENDIENTE:
            raise EstadoInvalido(
                "Una operación empezada o terminada no se quita: marcala como no realizada"
            )
        if item.tiene_precio and not self.precios_editables:
            raise EstadoInvalido(
                "El presupuesto ya fue aprobado: para quitar una operación con precio "
                "hay que volver a presupuestado"
            )
        self.items = [i for i in self.items if i.id != item_id]

    def reemplazar_item(self, item: ItemOT) -> None:
        self._exigir_editable()
        if not any(i.id == item.id for i in self.items):
            raise EstadoInvalido("La operación no existe en la OT")
        self.items = [item if i.id == item.id else i for i in self.items]

    def registrar_participacion(self, participacion: Participacion) -> None:
        self._exigir_editable()
        self.participaciones.append(participacion)

    def agregar_evidencia(self, evidencia: Evidencia) -> None:
        # La evidencia se puede agregar siempre; nunca se borra (RN-081, RN-084).
        self.evidencias.append(evidencia)

    def asignar_responsable(self, item_id: UUID, mecanico_id: UUID) -> None:
        self._exigir_editable()
        self.buscar_item(item_id).mecanico_id = mecanico_id

    # --- máquina de estados ------------------------------------------------
    def _puede(self, hacia: EstadoOT) -> bool:
        return hacia in _TRANSICIONES[self.estado]

    def _transicionar(self, hacia: EstadoOT) -> None:
        if not self._puede(hacia):
            raise EstadoInvalido(f"No se puede pasar de {self.estado.value} a {hacia.value}")
        self.estado = hacia

    def iniciar_revision(self) -> None:
        self._transicionar(EstadoOT.REVISION)

    def presupuestar(self, vigente_hasta: date | None = None) -> None:
        if not any(i.tiene_precio for i in self.items):
            raise EstadoInvalido("El presupuesto necesita al menos una operación con precio")
        self.presupuesto_vigente_hasta = vigente_hasta
        self._transicionar(EstadoOT.PRESUPUESTADO)

    def registrar_aprobacion(self, actor_id: UUID, canal: str, momento: datetime) -> None:
        if not canal.strip():
            raise SolicitudInvalida("Debe indicar el canal de aprobación")
        if (
            self.presupuesto_vigente_hasta is not None
            and momento.date() > self.presupuesto_vigente_hasta
        ):
            raise EstadoInvalido(
                "El presupuesto está vencido (RN-035): hay que re-presupuestar antes de aprobar"
            )
        self.aprobado_por = actor_id
        self.aprobado_canal = canal.strip()
        self.aprobado_en = momento
        self._transicionar(EstadoOT.EN_TALLER)

    def rechazar(self) -> None:
        self._transicionar(EstadoOT.RECHAZADO)

    def validar_cierre(self, actor_id: UUID, momento: datetime, nota: str | None = None) -> None:
        if not self.items:
            raise EstadoInvalido("No se puede validar una OT sin operaciones")
        pendientes = [
            i for i in self.items if i.estado in (EstadoItem.PENDIENTE, EstadoItem.EN_PROCESO)
        ]
        if pendientes:
            raise EstadoInvalido("Hay operaciones sin completar o marcar como no realizadas")
        self.validado_por = actor_id
        self.validado_en = momento
        self.validado_nota = nota
        self._transicionar(EstadoOT.PENDIENTE_PAGO)

    def marcar_cobrado(self) -> None:
        self._transicionar(EstadoOT.COBRADO)

    def entregar(self) -> None:
        self._transicionar(EstadoOT.ENTREGADO)

    def cerrar(self, momento: datetime) -> None:
        self.fecha_cierre = momento
        self._transicionar(EstadoOT.CERRADA)

    def cancelar(self) -> None:
        self._transicionar(EstadoOT.CANCELADA)

    def reabrir(self) -> None:
        # El control de "solo admin" vive en el caso de uso.
        self._transicionar(EstadoOT.PENDIENTE_PAGO)

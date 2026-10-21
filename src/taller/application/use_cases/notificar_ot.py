"""Notificaciones de OT (eventos del taller): creación, asignación, estado e inicio.

Mejor práctica (estilo Jira/Linear): cada evento puntual se emite una vez al
grupo que le interesa, y el badge vive hasta que la causa real desaparece.

- **OT nueva**: avisa a todo el taller (jefe/admin/recepción para asignar,
  mecánicos para saber que hay trabajo entrando). El aviso queda activo hasta
  que se asigne responsable — al asignar se marca leído automáticamente.
- **Cambio de estado**: todo el taller se entera (presupuestada, aprobada,
  lista para cobro, cancelada…).
- **Mecánico arrancó** (ítem a `en_proceso`): el taller ve «ya están
  trabajando sobre el auto».
"""
from __future__ import annotations

from decimal import Decimal

from taller.domain.entities.notificacion import Notificacion
from taller.domain.entities.orden_trabajo import OrdenTrabajo
from taller.domain.entities.usuario import Rol
from taller.domain.enums import Severidad, TipoNotificacion
from taller.domain.ports import Clock
from taller.domain.ports.notificaciones import NotificacionRepository, Notificador

#: Roles que se enteran de todo lo que pasa con una OT.
TODOS_EL_TALLER: tuple[Rol, ...] = (
    Rol.JEFE_TALLER,
    Rol.ADMINISTRACION,
    Rol.RECEPCION,
    Rol.MECANICO,
)

#: Roles que cobran y pagan (ven importes).
ROLES_COBRANZA: tuple[Rol, ...] = (Rol.ADMIN, Rol.ADMINISTRACION)


def pesos(monto: Decimal) -> str:
    return "$" + f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

ETIQUETA_ESTADO: dict[object, str] = {
    "iniciado": "ingresada",
    "revision": "en revisión",
    "presupuestado": "presupuestada",
    "rechazado": "rechazada",
    "en_taller": "en taller",
    "pendiente_pago": "prueba lista, falta cobro",
    "cobrado": "cobrada",
    "entregado": "entregada al cliente",
    "cerrada": "cerrada",
    "cancelada": "cancelada",
}


class NotificacionesOT:
    """Emisión concentrada: un solo criterio de títulos, mensajes y destinos."""

    def __init__(
        self,
        notificador: Notificador | None,
        notificaciones: NotificacionRepository | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._canal = notificador
        self._repo = notificaciones
        self._clock = clock

    @property
    def activo(self) -> bool:
        return self._canal is not None

    def _ahora(self) -> object:
        return self._clock.ahora() if self._clock is not None else None

    def _emitir(self, tipo: TipoNotificacion, titulo: str, mensaje: str, severidad: Severidad,
                ot_id: object) -> None:
        if self._canal is None:
            return
        momento = self._ahora()
        for rol in TODOS_EL_TALLER:
            self._canal.notificar(
                Notificacion(
                    tipo=tipo,
                    titulo=titulo,
                    mensaje=mensaje,
                    severidad=severidad,
                    referencia_tipo="orden_trabajo",
                    referencia_id=ot_id,  # type: ignore[arg-type]
                    rol_destino=rol,
                    creada_en=momento,  # type: ignore[arg-type]
                )
            )

    def nueva(self, ot: OrdenTrabajo, patente: str) -> None:
        self._emitir(
            TipoNotificacion.OT_SIN_ASIGNAR,
            f"{ot.codigo} nueva — {patente}",
            "Orden de trabajo creada. Falta asignar responsable.",
            Severidad.ADVERTENCIA,
            ot.id,
        )

    def asignada(self, ot: OrdenTrabajo, patente: str, responsable: str) -> None:
        # El aviso «sin asignar» ya no aplica: la causa desapareció.
        if self._repo is not None:
            self._repo.marcar_leidas_por_referencia(
                referencia_tipo="orden_trabajo", referencia_id=ot.id
            )
        self._emitir(
            TipoNotificacion.OT_ASIGNADA,
            f"{ot.codigo} asignada — {patente}",
            f"Responsable: {responsable}. Ingresá a la orden para ver las operaciones.",
            Severidad.INFO,
            ot.id,
        )

    def estado(self, ot: OrdenTrabajo, patente: str) -> None:
        etiqueta = ETIQUETA_ESTADO.get(ot.estado.value, ot.estado.value)
        self._emitir(
            TipoNotificacion.OT_ESTADO,
            f"{ot.codigo} {etiqueta} — {patente}",
            f"La {ot.codigo} ({patente}) pasó a «{etiqueta}».",
            Severidad.INFO,
            ot.id,
        )

    def por_cobrar(self, ot: OrdenTrabajo, resumen: str, saldo: Decimal) -> None:
        """Sólo a quien maneja la plata: el mecánico no ve importes (RN-106)."""
        if self._canal is None:
            return
        momento = self._ahora()
        for rol in ROLES_COBRANZA:
            self._canal.notificar(
                Notificacion(
                    tipo=TipoNotificacion.OT_POR_COBRAR,
                    titulo=f"Cobrar {ot.codigo}: {pesos(saldo)}",
                    mensaje=(
                        f"La {ot.codigo} ({resumen}) está terminada y falta cobrarla. "
                        "Quedó en «Por cobrar» del cliente."
                    ),
                    severidad=Severidad.ADVERTENCIA,
                    referencia_tipo="orden_trabajo",
                    referencia_id=ot.id,
                    rol_destino=rol,
                    creada_en=momento,  # type: ignore[arg-type]
                )
            )

    def cobrada(self, ot: OrdenTrabajo, resumen: str) -> None:
        # Los avisos «falta cobro» ya no aplican: la causa desapareció.
        if self._repo is not None:
            self._repo.marcar_leidas_por_referencia(
                referencia_tipo="orden_trabajo", referencia_id=ot.id
            )
        self.estado(ot, resumen)

    def trabajando(self, ot: OrdenTrabajo, patente: str, mecanico: str) -> None:
        self._emitir(
            TipoNotificacion.OT_EN_PROCESO,
            f"Trabajando en {ot.codigo} — {patente}",
            f"{mecanico} empezó a trabajar en la {ot.codigo} ({patente}).",
            Severidad.INFO,
            ot.id,
        )

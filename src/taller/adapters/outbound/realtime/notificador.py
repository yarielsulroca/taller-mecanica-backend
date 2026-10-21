from __future__ import annotations

from taller.adapters.outbound.realtime.bus import BusEnMemoria
from taller.domain.entities.notificacion import Notificacion
from taller.domain.ports.notificaciones import NotificacionRepository


class NotificadorRepoBus:
    """Persiste la notificación y la publica en el bus para push inmediato."""

    def __init__(self, repo: NotificacionRepository, bus: BusEnMemoria) -> None:
        self._repo = repo
        self._bus = bus

    def notificar(self, notificacion: Notificacion) -> None:
        self._repo.guardar(notificacion)
        self._bus.publicar(
            {
                "id": str(notificacion.id),
                "tipo": notificacion.tipo.value,
                "titulo": notificacion.titulo,
                "mensaje": notificacion.mensaje,
                "severidad": notificacion.severidad.value,
                "referencia_tipo": notificacion.referencia_tipo,
                "referencia_id": (
                    str(notificacion.referencia_id) if notificacion.referencia_id else None
                ),
                "rol_destino": notificacion.rol_destino.value if notificacion.rol_destino else None,
                "usuario_id": str(notificacion.usuario_id) if notificacion.usuario_id else None,
            }
        )

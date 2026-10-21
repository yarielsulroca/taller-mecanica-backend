"""Caso de uso de auditoría: registrar acciones sensibles y consultarlas."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from taller.domain.entities.auditoria import Auditoria
from taller.domain.entities.usuario import Usuario
from taller.domain.ports import Clock
from taller.domain.ports.auditoria import AuditoriaRepository


class RegistrarAuditoria:
    """Appenda-only: registra, jamás edita ni elimina."""

    def __init__(self, repo: AuditoriaRepository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def execute(
        self,
        usuario: Usuario,
        *,
        accion: str,
        entidad: str,
        entidad_id: UUID,
        detalle: str | None = None,
        datos_antes: dict[str, object] | None = None,
        datos_despues: dict[str, object] | None = None,
        motivo: str | None = None,
    ) -> Auditoria:
        registro = Auditoria(
            usuario_id=usuario.id,
            usuario_nombre=usuario.nombre,
            rol=",".join(r.value for r in usuario.roles),
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=detalle,
            datos_antes=datos_antes,
            datos_despues=datos_despues,
            motivo=motivo,
            fecha=self._clock.ahora(),
        )
        self._repo.guardar(registro)
        return registro


@dataclass(frozen=True, slots=True)
class ConsultarAuditoriaQuery:
    accion: str | None = None
    entidad: str | None = None
    entidad_id: UUID | None = None
    usuario_id: UUID | None = None
    desde: datetime | None = None
    hasta: datetime | None = None


class ConsultarAuditoria:
    def __init__(self, repo: AuditoriaRepository) -> None:
        self._repo = repo

    def execute(self, query: ConsultarAuditoriaQuery) -> list[Auditoria]:
        return self._repo.listar(
            accion=query.accion,
            entidad=query.entidad,
            entidad_id=query.entidad_id,
            usuario_id=query.usuario_id,
            desde=query.desde,
            hasta=query.hasta,
        )
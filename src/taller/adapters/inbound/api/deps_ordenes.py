from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_container, get_session
from taller.adapters.inbound.api.deps_maestros import (
    repo_clientes,
    repo_vehiculos,
)
from taller.adapters.inbound.api.deps_notificaciones import notificador, repo_notificaciones
from taller.adapters.outbound.postgres.finanzas_repository import (
    SqlCuotaRepository,
    SqlMovimientoRepository,
)
from taller.adapters.outbound.postgres.maestros_repositories import (
    SqlClienteRepository,
    SqlTrabajadorRepository,
    SqlVehiculoRepository,
)
from taller.adapters.outbound.postgres.notificaciones_repository import SqlNotificacionRepository
from taller.adapters.outbound.postgres.ordenes_repository import SqlOrdenTrabajoRepository
from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
from taller.application.use_cases.cobranza_ot import CobranzaOT
from taller.application.use_cases.historial_vehiculo import HistorialVehiculo
from taller.application.use_cases.notificar_ot import NotificacionesOT
from taller.application.use_cases.ordenes import (
    AbrirOT,
    AgendaDelDia,
    AgregarItem,
    AgregarNotaItem,
    AgregarNotaOT,
    AsignarResponsable,
    CambiarEstadoItem,
    CancelarOT,
    CerrarOrden,
    EditarItem,
    Entregar,
    ListarOT,
    MarcarCobrada,
    ObtenerOT,
    Presupuestar,
    QuitarItem,
    ReabrirOT,
    RechazarPresupuesto,
    RegistrarAprobacion,
    RegistrarParticipacion,
    RegistrarRevision,
    SubirEvidencia,
    ValidarCierre,
)
from taller.container import Container


def repo_ordenes(session: Annotated[Session, Depends(get_session)]) -> SqlOrdenTrabajoRepository:
    return SqlOrdenTrabajoRepository(session)


def repo_trabajadores_ordenes(
    session: Annotated[Session, Depends(get_session)],
) -> SqlTrabajadorRepository:
    return SqlTrabajadorRepository(session)


def avisos_ot(
    canal: Annotated[NotificadorRepoBus, Depends(notificador)],
    repo: Annotated[SqlNotificacionRepository, Depends(repo_notificaciones)],
    container: Annotated[Container, Depends(get_container)],
) -> NotificacionesOT:
    """Canal central de avisos de OT (SSE + centro de notificaciones)."""
    return NotificacionesOT(canal, repo, container.clock)


def cobranza_ot(
    session: Annotated[Session, Depends(get_session)],
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    container: Annotated[Container, Depends(get_container)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
) -> CobranzaOT:
    return CobranzaOT(
        ordenes,
        SqlCuotaRepository(session),
        SqlMovimientoRepository(session),
        container.clock,
        avisos,
    )


def uc_abrir_ot(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    vehiculos: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
    clientes: Annotated[SqlClienteRepository, Depends(repo_clientes)],
    container: Annotated[Container, Depends(get_container)],
    notif: Annotated[NotificadorRepoBus, Depends(notificador)],
) -> AbrirOT:
    return AbrirOT(ordenes, vehiculos, clientes, container.clock, notif)


def uc_obtener_ot(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> ObtenerOT:
    return ObtenerOT(ordenes)


def uc_listar_ot(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> ListarOT:
    return ListarOT(ordenes)


def uc_historial_vehiculo(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    vehiculos: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
) -> HistorialVehiculo:
    return HistorialVehiculo(ordenes, vehiculos)


def uc_agenda(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> AgendaDelDia:
    return AgendaDelDia(ordenes)


def uc_registrar_revision(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> RegistrarRevision:
    return RegistrarRevision(ordenes)


def uc_agregar_item(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> AgregarItem:
    return AgregarItem(ordenes)


def uc_editar_item(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> EditarItem:
    return EditarItem(ordenes)


def uc_quitar_item(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> QuitarItem:
    return QuitarItem(ordenes)


def uc_asignar_responsable(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
    trabajadores: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores_ordenes)],
) -> AsignarResponsable:
    return AsignarResponsable(ordenes, avisos, trabajadores)


def uc_cambiar_estado_item(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
    trabajadores: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores_ordenes)],
) -> CambiarEstadoItem:
    return CambiarEstadoItem(ordenes, avisos, trabajadores)


def uc_presupuestar(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
) -> Presupuestar:
    return Presupuestar(ordenes, avisos)


def uc_registrar_aprobacion(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    container: Annotated[Container, Depends(get_container)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
) -> RegistrarAprobacion:
    return RegistrarAprobacion(ordenes, container.clock, avisos)


def uc_rechazar_presupuesto(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
) -> RechazarPresupuesto:
    return RechazarPresupuesto(ordenes, avisos)


def uc_registrar_participacion(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> RegistrarParticipacion:
    return RegistrarParticipacion(ordenes)


def uc_agregar_nota_ot(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> AgregarNotaOT:
    return AgregarNotaOT(ordenes)


def uc_agregar_nota_item(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> AgregarNotaItem:
    return AgregarNotaItem(ordenes)


def uc_validar_cierre(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    container: Annotated[Container, Depends(get_container)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
    cobranza: Annotated[CobranzaOT, Depends(cobranza_ot)],
) -> ValidarCierre:
    return ValidarCierre(ordenes, container.clock, avisos, cobranza)


def uc_marcar_cobrada(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
) -> MarcarCobrada:
    return MarcarCobrada(ordenes, avisos)


def uc_entregar(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
) -> Entregar:
    return Entregar(ordenes, avisos)


def uc_cerrar_orden(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    container: Annotated[Container, Depends(get_container)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
) -> CerrarOrden:
    return CerrarOrden(ordenes, container.clock, avisos)


def uc_cancelar_ot(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
) -> CancelarOT:
    return CancelarOT(ordenes, avisos)


def uc_reabrir_ot(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    avisos: Annotated[NotificacionesOT, Depends(avisos_ot)],
    cobranza: Annotated[CobranzaOT, Depends(cobranza_ot)],
) -> ReabrirOT:
    return ReabrirOT(ordenes, avisos, cobranza)


def uc_subir_evidencia(
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
    container: Annotated[Container, Depends(get_container)],
) -> SubirEvidencia:
    return SubirEvidencia(ordenes, container.storage, container.clock)

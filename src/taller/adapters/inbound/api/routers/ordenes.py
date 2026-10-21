from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session as OrmSession

from taller.adapters.inbound.api.deps import (
    get_container,
    get_current_user,
    get_session,
    require_roles,
)
from taller.adapters.inbound.api.deps_auditoria import uc_registrar_auditoria
from taller.adapters.inbound.api.deps_ordenes import (
    uc_abrir_ot,
    uc_agenda,
    uc_agregar_item,
    uc_agregar_nota_item,
    uc_agregar_nota_ot,
    uc_asignar_responsable,
    uc_cambiar_estado_item,
    uc_cancelar_ot,
    uc_cerrar_orden,
    uc_editar_item,
    uc_entregar,
    uc_historial_vehiculo,
    uc_listar_ot,
    uc_marcar_cobrada,
    uc_obtener_ot,
    uc_presupuestar,
    uc_quitar_item,
    uc_reabrir_ot,
    uc_rechazar_presupuesto,
    uc_registrar_aprobacion,
    uc_registrar_participacion,
    uc_registrar_revision,
    uc_subir_evidencia,
    uc_validar_cierre,
)
from taller.adapters.inbound.api.schemas_ordenes import (
    AbrirOTRequest,
    AprobacionRequest,
    CancelarRequest,
    ItemCreate,
    ItemEstadoRequest,
    ItemUpdate,
    NotaRequest,
    OTResponse,
    OTResponseOperativa,
    ParticipacionRequest,
    PresupuestarRequest,
    ResponsableRequest,
    RevisionRequest,
    ValidarRequest,
)
from taller.adapters.outbound.postgres.configuracion_repository import (
    SqlConfiguracionTallerRepository,
)
from taller.adapters.outbound.postgres.maestros_repositories import SqlClienteRepository
from taller.application.use_cases.auditoria import RegistrarAuditoria
from taller.application.use_cases.historial_vehiculo import (
    HistorialVehiculo,
    HistorialVehiculoQuery,
)
from taller.application.use_cases.ordenes import (
    AbrirOT,
    AbrirOTCommand,
    AgendaDelDia,
    AgendaDelDiaQuery,
    AgregarItem,
    AgregarItemCommand,
    AgregarNotaItem,
    AgregarNotaItemCommand,
    AgregarNotaOT,
    AgregarNotaOTCommand,
    AsignarResponsable,
    AsignarResponsableCommand,
    CambiarEstadoItem,
    CambiarEstadoItemCommand,
    CancelarOT,
    CancelarOTCommand,
    CerrarOrden,
    CerrarOrdenCommand,
    EditarItem,
    EditarItemCommand,
    Entregar,
    EntregarCommand,
    ListarOT,
    ListarOTQuery,
    MarcarCobrada,
    MarcarCobradaCommand,
    ObtenerOT,
    Presupuestar,
    PresupuestarCommand,
    QuitarItem,
    QuitarItemCommand,
    ReabrirOT,
    ReabrirOTCommand,
    RechazarPresupuesto,
    RechazarPresupuestoCommand,
    RegistrarAprobacion,
    RegistrarAprobacionCommand,
    RegistrarParticipacion,
    RegistrarParticipacionCommand,
    RegistrarRevision,
    RegistrarRevisionCommand,
    SubirEvidencia,
    SubirEvidenciaCommand,
    ValidarCierre,
    ValidarCierreCommand,
)
from taller.container import Container
from taller.domain.entities.orden_trabajo import OrdenTrabajo
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.enums import EstadoOT, MomentoEvidencia, TipoEvidencia
from taller.domain.exceptions import SinPermiso
from taller.domain.ports.storage import ArchivoStorage

Autenticado = Annotated[Usuario, Depends(get_current_user)]
_puede_validar = require_roles(Rol.ADMIN, Rol.ADMINISTRACION, Rol.JEFE_TALLER)
Validador = Annotated[Usuario, Depends(_puede_validar)]
Cancelador = Annotated[Usuario, Depends(_puede_validar)]
SoloAdmin = Annotated[Usuario, Depends(require_roles(Rol.ADMIN))]

# Solo estos roles ven importes. Con `mecanico` (o `recepcion`) en la mezcla de
# roles no se ven: el rol más restrictivo domina la visibilidad (RN-106/107),
# aunque las acciones sí se combinan (unión de permisos).
_ROLES_CON_ECONOMIA = frozenset({Rol.ADMIN, Rol.ADMINISTRACION, Rol.JEFE_TALLER})


def _storage_evidencia_(
    container: Annotated[Container, Depends(get_container)],
) -> ArchivoStorage:
    return container.storage

# Imprimibles (PDF vía imprimir del navegador): llevan importes, mismo criterio
# de visibilidad RN-106 — sólo los roles con economía; recepción/mecánico no.
Imprimible = Annotated[
    Usuario, Depends(require_roles(Rol.ADMIN, Rol.ADMINISTRACION, Rol.JEFE_TALLER))
]

OTVista = OTResponse | OTResponseOperativa


def _repo_clientes_(
    session: Annotated[OrmSession, Depends(get_session)],
) -> SqlClienteRepository:
    return SqlClienteRepository(session)


def _repo_configuracion_(
    session: Annotated[OrmSession, Depends(get_session)],
) -> SqlConfiguracionTallerRepository:
    return SqlConfiguracionTallerRepository(session)


_CSS = """
body { font: 12pt/1.4 Georgia, serif; margin: 24px auto; max-width: 720px; color: #111; }
h1 { font-size: 16pt; margin: 0; }
.muted { color: #555; }
table { width: 100%; border-collapse: collapse; margin-top: 16px; }
th, td { text-align: left; border-bottom: 1px solid #ccc; padding: 6px 4px; }
td.num, th.num { text-align: right; }
.totales td { border: none; font-weight: bold; }
.caja { border: 1px solid #999; padding: 8px 12px; margin: 12px 0; }
@media print { .print-btn { display: none; } }
.print-btn { position: fixed; top: 8px; right: 8px; padding: 6px 14px; }
"""


def _base_html(titulo: str, taller: str, cuit: str, cuerpo: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es-ar"><head><meta charset="utf-8"><title>{titulo}</title>
<style>{_CSS}</style></head><body>
<div><h1>{taller}</h1><div class="muted">CUIT {cuit}</div></div>
<button class="print-btn" onclick="window.print()">Imprimir / Guardar PDF</button>
{cuerpo}
</body></html>"""


def _dinero(monto: Decimal) -> str:
    """Formato 1.234,56 (iso RI style)."""
    texto = f"{monto:,.2f}".replace(",", "@").replace(".", ",")
    return texto.replace("@", ".")


router = APIRouter(prefix="/ordenes", tags=["ordenes"])


def _ver_economia(usuario: Usuario) -> bool:
    """Importes visibles sólo para jefe/admin (mecánico y recepción: nunca, RN-106)."""
    return bool(usuario.roles & _ROLES_CON_ECONOMIA)


def _vista(ot: OrdenTrabajo, usuario: Usuario) -> OTVista:
    if _ver_economia(usuario):
        return OTResponse.from_domain(ot)
    return OTResponseOperativa.from_domain(ot)


def _exigir_sin_precios(usuario: Usuario, payload: ItemCreate) -> None:
    if not _ver_economia(usuario) and (payload.precio_unitario > 0 or payload.descuento > 0):
        raise SinPermiso("El mecánico no puede cargar ni modificar precios")


@router.post("", response_model=OTVista, status_code=status.HTTP_201_CREATED)
def abrir_ot(
    usuario: Autenticado,
    payload: AbrirOTRequest,
    uc: Annotated[AbrirOT, Depends(uc_abrir_ot)],
) -> OTVista:
    return _vista(uc.execute(AbrirOTCommand(**payload.model_dump())), usuario)


@router.get("", response_model=list[OTVista])
def listar_ot(
    usuario: Autenticado,
    uc: Annotated[ListarOT, Depends(uc_listar_ot)],
    estado: Annotated[EstadoOT | None, Query()] = None,
    cliente_id: Annotated[UUID | None, Query()] = None,
    vehiculo_id: Annotated[UUID | None, Query()] = None,
    mecanico_id: Annotated[UUID | None, Query()] = None,
    del_dia: Annotated[date | None, Query()] = None,
) -> list[OTVista]:
    query = ListarOTQuery(
        estado=estado,
        cliente_id=cliente_id,
        vehiculo_id=vehiculo_id,
        mecanico_id=mecanico_id,
        del_dia=del_dia,
    )
    return [_vista(o, usuario) for o in uc.execute(query)]


@router.get("/agenda", response_model=list[OTVista])
def agenda_del_dia(
    usuario: Autenticado,
    uc: Annotated[AgendaDelDia, Depends(uc_agenda)],
    mecanico_id: Annotated[UUID | None, Query()] = None,
    dia: Annotated[date | None, Query()] = None,
) -> list[OTVista]:
    query = AgendaDelDiaQuery(mecanico_id=mecanico_id, dia=dia)
    return [_vista(o, usuario) for o in uc.execute(query)]


@router.get("/historial/{vehiculo_id}", response_model=list[OTVista])
def historial_vehiculo(
    vehiculo_id: UUID,
    usuario: Autenticado,
    uc: Annotated[HistorialVehiculo, Depends(uc_historial_vehiculo)],
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> list[OTVista]:
    """Órdenes del vehículo, de la más nueva a la más vieja; ``q`` busca en lo que se hizo."""
    query = HistorialVehiculoQuery(vehiculo_id=vehiculo_id, desde=desde, hasta=hasta, q=q)
    return [_vista(o, usuario) for o in uc.execute(query)]


@router.get("/{ot_id}", response_model=OTVista)
def obtener_ot(
    ot_id: UUID,
    usuario: Autenticado,
    uc: Annotated[ObtenerOT, Depends(uc_obtener_ot)],
) -> OTVista:
    return _vista(uc.execute(ot_id), usuario)


@router.post("/{ot_id}/revision", response_model=OTVista)
def registrar_revision(
    ot_id: UUID,
    usuario: Autenticado,
    payload: RevisionRequest,
    uc: Annotated[RegistrarRevision, Depends(uc_registrar_revision)],
) -> OTVista:
    cmd = RegistrarRevisionCommand(ot_id=ot_id, diagnostico=payload.diagnostico)
    return _vista(uc.execute(cmd), usuario)


@router.post("/{ot_id}/items", response_model=OTVista, status_code=status.HTTP_201_CREATED)
def agregar_item(
    ot_id: UUID,
    usuario: Autenticado,
    payload: ItemCreate,
    uc: Annotated[AgregarItem, Depends(uc_agregar_item)],
) -> OTVista:
    _exigir_sin_precios(usuario, payload)
    return _vista(uc.execute(AgregarItemCommand(ot_id=ot_id, **payload.model_dump())), usuario)


@router.patch("/{ot_id}/items/{item_id}", response_model=OTVista)
def editar_item(
    ot_id: UUID,
    item_id: UUID,
    usuario: Autenticado,
    payload: ItemUpdate,
    uc: Annotated[EditarItem, Depends(uc_editar_item)],
) -> OTVista:
    _exigir_sin_precios(usuario, payload)
    cmd = EditarItemCommand(
        ot_id=ot_id,
        item_id=item_id,
        con_importes=_ver_economia(usuario),
        **payload.model_dump(),
    )
    return _vista(uc.execute(cmd), usuario)


@router.delete("/{ot_id}/items/{item_id}", response_model=OTVista)
def quitar_item(
    ot_id: UUID,
    item_id: UUID,
    usuario: Autenticado,
    uc: Annotated[QuitarItem, Depends(uc_quitar_item)],
) -> OTVista:
    cmd = QuitarItemCommand(ot_id=ot_id, item_id=item_id, con_importes=_ver_economia(usuario))
    return _vista(uc.execute(cmd), usuario)


@router.post("/{ot_id}/items/{item_id}/estado", response_model=OTVista)
def cambiar_estado_item(
    ot_id: UUID,
    item_id: UUID,
    usuario: Autenticado,
    payload: ItemEstadoRequest,
    uc: Annotated[CambiarEstadoItem, Depends(uc_cambiar_estado_item)],
) -> OTVista:
    cmd = CambiarEstadoItemCommand(
        ot_id=ot_id, item_id=item_id, accion=payload.accion, motivo=payload.motivo
    )
    return _vista(uc.execute(cmd), usuario)


@router.post("/{ot_id}/items/{item_id}/responsable", response_model=OTVista)
def asignar_responsable(
    ot_id: UUID,
    item_id: UUID,
    usuario: Autenticado,
    payload: ResponsableRequest,
    uc: Annotated[AsignarResponsable, Depends(uc_asignar_responsable)],
) -> OTVista:
    cmd = AsignarResponsableCommand(ot_id=ot_id, item_id=item_id, mecanico_id=payload.mecanico_id)
    return _vista(uc.execute(cmd), usuario)


@router.post("/{ot_id}/items/{item_id}/nota", response_model=OTVista)
def agregar_nota_item(
    ot_id: UUID,
    item_id: UUID,
    usuario: Autenticado,
    payload: NotaRequest,
    uc: Annotated[AgregarNotaItem, Depends(uc_agregar_nota_item)],
) -> OTVista:
    cmd = AgregarNotaItemCommand(ot_id=ot_id, item_id=item_id, nota=payload.nota)
    return _vista(uc.execute(cmd), usuario)


@router.post("/{ot_id}/presupuestar", response_model=OTVista)
def presupuestar(
    ot_id: UUID,
    usuario: Autenticado,
    uc: Annotated[Presupuestar, Depends(uc_presupuestar)],
    payload: PresupuestarRequest | None = None,
) -> OTVista:
    vigente = payload.vigente_hasta if payload is not None else None
    return _vista(uc.execute(PresupuestarCommand(ot_id=ot_id, vigente_hasta=vigente)), usuario)


@router.post("/{ot_id}/aprobacion", response_model=OTVista)
def registrar_aprobacion(
    ot_id: UUID,
    usuario: Autenticado,
    payload: AprobacionRequest,
    uc: Annotated[RegistrarAprobacion, Depends(uc_registrar_aprobacion)],
    audit: Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)],
) -> OTVista:
    cmd = RegistrarAprobacionCommand(ot_id=ot_id, actor_id=usuario.id, canal=payload.canal)
    ot = uc.execute(cmd)
    audit.execute(
        usuario,
        accion="aprobar",
        entidad="orden_trabajo",
        entidad_id=ot.id,
        detalle=f"OT #{ot.numero} — presupuesto aprobado por {payload.canal}",
    )
    return _vista(ot, usuario)


@router.post("/{ot_id}/rechazo", response_model=OTVista)
def rechazar_presupuesto(
    ot_id: UUID,
    usuario: Autenticado,
    uc: Annotated[RechazarPresupuesto, Depends(uc_rechazar_presupuesto)],
) -> OTVista:
    return _vista(uc.execute(RechazarPresupuestoCommand(ot_id=ot_id)), usuario)


@router.post("/{ot_id}/participaciones", response_model=OTVista)
def registrar_participacion(
    ot_id: UUID,
    usuario: Autenticado,
    payload: ParticipacionRequest,
    uc: Annotated[RegistrarParticipacion, Depends(uc_registrar_participacion)],
) -> OTVista:
    cmd = RegistrarParticipacionCommand(ot_id=ot_id, **payload.model_dump())
    return _vista(uc.execute(cmd), usuario)


@router.post("/{ot_id}/nota", response_model=OTVista)
def agregar_nota_ot(
    ot_id: UUID,
    usuario: Autenticado,
    payload: NotaRequest,
    uc: Annotated[AgregarNotaOT, Depends(uc_agregar_nota_ot)],
) -> OTVista:
    return _vista(uc.execute(AgregarNotaOTCommand(ot_id=ot_id, nota=payload.nota)), usuario)


@router.post("/{ot_id}/validar", response_model=OTVista)
def validar_cierre(
    ot_id: UUID,
    usuario: Validador,
    payload: ValidarRequest,
    uc: Annotated[ValidarCierre, Depends(uc_validar_cierre)],
    audit: Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)],
) -> OTVista:
    cmd = ValidarCierreCommand(ot_id=ot_id, actor_id=usuario.id, nota=payload.nota)
    ot = uc.execute(cmd)
    audit.execute(
        usuario,
        accion="validar",
        entidad="orden_trabajo",
        entidad_id=ot.id,
        detalle=f"OT #{ot.numero} — cierre técnico validado",
    )
    return _vista(ot, usuario)


@router.post("/{ot_id}/cancelar", response_model=OTVista)
def cancelar_ot(
    ot_id: UUID,
    usuario: Cancelador,
    payload: CancelarRequest,
    uc: Annotated[CancelarOT, Depends(uc_cancelar_ot)],
    audit: Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)],
) -> OTVista:
    ot = uc.execute(CancelarOTCommand(ot_id=ot_id, motivo=payload.motivo))
    audit.execute(
        usuario,
        accion="cancelar",
        entidad="orden_trabajo",
        entidad_id=ot.id,
        detalle=f"OT #{ot.numero} — {payload.motivo or 'sin motivo'}",
    )
    return _vista(ot, usuario)


@router.post("/{ot_id}/reabrir", response_model=OTVista)
def reabrir_ot(
    ot_id: UUID,
    usuario: SoloAdmin,
    uc: Annotated[ReabrirOT, Depends(uc_reabrir_ot)],
) -> OTVista:
    return _vista(uc.execute(ReabrirOTCommand(ot_id=ot_id)), usuario)


@router.post("/{ot_id}/evidencias", response_model=OTVista, status_code=status.HTTP_201_CREATED)
async def subir_evidencia(
    ot_id: UUID,
    usuario: Autenticado,
    uc: Annotated[SubirEvidencia, Depends(uc_subir_evidencia)],
    tipo: Annotated[TipoEvidencia, Form()],
    momento: Annotated[MomentoEvidencia, Form()],
    archivo: Annotated[UploadFile, File()],
    item_id: Annotated[UUID | None, Form()] = None,
    nota: Annotated[str | None, Form()] = None,
) -> OTVista:
    contenido = await archivo.read()
    cmd = SubirEvidenciaCommand(
        ot_id=ot_id,
        autor_id=usuario.id,
        tipo=tipo,
        momento=momento,
        nombre_original=archivo.filename or "archivo",
        contenido=contenido,
        content_type=archivo.content_type or "",
        item_id=item_id,
        nota=nota,
    )
    return _vista(uc.execute(cmd), usuario)


@router.get(
    "/{ot_id}/evidencias/{evidencia_id}/archivo",
    response_class=FileResponse,
    responses={200: {"content": {"image/*": {}, "video/*": {}}}},
)
def archivo_evidencia(
    ot_id: UUID,
    evidencia_id: UUID,
    _: Autenticado,
    uc: Annotated[ObtenerOT, Depends(uc_obtener_ot)],
    storage: Annotated[ArchivoStorage, Depends(_storage_evidencia_)],
) -> FileResponse:
    """Sirve la foto/video original (preview del panel + descarga)."""
    ot = uc.execute(ot_id)
    evidencia = next((e for e in ot.evidencias if e.id == evidencia_id), None)
    if evidencia is None:
        raise SinPermiso("La evidencia no existe en esta orden")
    media = evidencia.content_type or (
        "video/mp4" if evidencia.tipo is TipoEvidencia.VIDEO else "image/jpeg"
    )
    return FileResponse(
        storage.ruta_fisica(evidencia.archivo_path),
        media_type=media,
        filename=evidencia.nombre_original,
        content_disposition_type="inline",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/{ot_id}/cobrar", response_model=OTVista)
def marcar_cobrada(
    ot_id: UUID,
    usuario: Validador,
    uc: Annotated[MarcarCobrada, Depends(uc_marcar_cobrada)],
) -> OTVista:
    """`pendiente_pago → cobrado`: un paso del flujo (el cobro real se registra en Cobros)."""
    return _vista(uc.execute(MarcarCobradaCommand(ot_id=ot_id)), usuario)


@router.post("/{ot_id}/entregar", response_model=OTVista)
def entregar_ot(
    ot_id: UUID,
    usuario: Validador,
    uc: Annotated[Entregar, Depends(uc_entregar)],
) -> OTVista:
    return _vista(uc.execute(EntregarCommand(ot_id=ot_id)), usuario)


@router.post("/{ot_id}/cerrar", response_model=OTVista)
def cerrar_orden(
    ot_id: UUID,
    usuario: SoloAdmin,
    uc: Annotated[CerrarOrden, Depends(uc_cerrar_orden)],
) -> OTVista:
    return _vista(uc.execute(CerrarOrdenCommand(ot_id=ot_id)), usuario)


# --- Presupuesto / OT imprimibles (P3: HTML listo para imprimir a PDF) -------
def _cabecera(ot_id: UUID, cliente_nombre: str | None) -> str:
    return (
        f'<div class="caja"><strong>OT #{ot_id}</strong><br>Cliente: {cliente_nombre or "—"}</div>'
    )


@router.get("/{ot_id}/presupuesto", response_class=HTMLResponse)
def presupuesto_imprimible(
    ot_id: UUID,
    usuario: Imprimible,
    uc: Annotated[ObtenerOT, Depends(uc_obtener_ot)],
    clientes: Annotated[SqlClienteRepository, Depends(_repo_clientes_)],
    configuracion: Annotated[SqlConfiguracionTallerRepository, Depends(_repo_configuracion_)],
) -> HTMLResponse:
    """Presupuesto listo para imprimir/guardar como PDF desde el navegador."""
    ot = uc.execute(ot_id)
    cliente = clientes.obtener(ot.cliente_id)
    taller = configuracion.obtener()
    taller_nombre = taller.razon_social if taller else "Taller Mecánico"
    taller_cuit = str(taller.cuit) if taller else ""
    desde_hasta = ot.presupuesto_vigente_hasta
    vigente = (
        f"Válido hasta {desde_hasta.strftime('%d/%m/%Y')}" if desde_hasta else "Sin plazo definido"
    )
    filas = "".join(
        f"<tr><td>{i.descripcion}</td><td>{i.tipo.value}</td>"
        f"<td class='num'>{i.cantidad}</td><td class='num'>{_dinero(i.precio_unitario)}</td>"
        f"<td class='num'>{_dinero(i.subtotal)}</td></tr>"
        for i in ot.items
    )
    cuerpo = (
        "<h1>Presupuesto</h1>"
        f"{_cabecera(ot.id, getattr(cliente, 'nombre', None))}"
        f"<p class='muted'>{vigente}</p>"
        "<table><tr><th>Operación</th><th>Tipo</th><th class='num'>Cant.</th>"
        "<th class='num'>Precio</th><th class='num'>Subtotal</th></tr>"
        f"{filas or '<tr><td colspan=5 class=muted>Sin operaciones todavía</td></tr>'}</table>"
        "<table class='totales'>"
        f"<tr><td>Total</td><td class='num'>{_dinero(ot.total)}</td></tr></table>"
        "<p class='muted'>El presupuesto aprobado por el cliente se toma como base del trabajo.</p>"
    )
    return HTMLResponse(_base_html("Presupuesto OT", taller_nombre, taller_cuit, cuerpo))


@router.get("/{ot_id}/impresion", response_class=HTMLResponse)
def ot_imprimible(
    ot_id: UUID,
    usuario: Imprimible,
    uc: Annotated[ObtenerOT, Depends(uc_obtener_ot)],
    clientes: Annotated[SqlClienteRepository, Depends(_repo_clientes_)],
    configuracion: Annotated[SqlConfiguracionTallerRepository, Depends(_repo_configuracion_)],
) -> HTMLResponse:
    """Orden de trabajo completa para física en el taller (incluye precios)."""
    ot = uc.execute(ot_id)
    cliente = clientes.obtener(ot.cliente_id)
    taller = configuracion.obtener()
    taller_nombre = taller.razon_social if taller else "Taller Mecánico"
    taller_cuit = str(taller.cuit) if taller else ""
    filas = "".join(
        f"<tr><td>{i.descripcion}</td><td>{i.tipo.value}</td>"
        f"<td>{i.estado.value}</td><td class='num'>{_dinero(i.subtotal)}</td></tr>"
        for i in ot.items
    )
    cuerpo = (
        "<h1>Orden de Trabajo</h1>"
        f"{_cabecera(ot.id, getattr(cliente, 'nombre', None))}"
        f"<p class='muted'>Estado: {ot.estado.value}</p>"
        "<table><tr><th>Operación</th><th>Tipo</th><th>Estado</th>"
        "<th class='num'>Subtotal</th></tr>"
        f"{filas or '<tr><td colspan=4 class=muted>Sin operaciones todavía</td></tr>'}</table>"
        "<table class='totales'>"
        f"<tr><td>Total</td><td class='num'>{_dinero(ot.total)}</td></tr></table>"
    )
    return HTMLResponse(_base_html("Orden de Trabajo", taller_nombre, taller_cuit, cuerpo))

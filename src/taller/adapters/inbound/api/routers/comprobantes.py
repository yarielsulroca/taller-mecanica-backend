from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from taller.adapters.inbound.api.deps import require_roles
from taller.adapters.inbound.api.deps_auditoria import uc_registrar_auditoria
from taller.adapters.inbound.api.deps_comprobantes import (
    uc_actualizar_comprobante,
    uc_anular_comprobante,
    uc_comprobar_comprobante,
    uc_listar_comprobantes,
    uc_obtener_comprobante,
    uc_preview_comprobante,
    uc_registrar_comprobante,
)
from taller.adapters.inbound.api.schemas_comprobantes import (
    ComprobanteCreate,
    ComprobanteResponse,
    ComprobanteUpdate,
    OcrPreviewResponse,
)
from taller.application.use_cases.auditoria import RegistrarAuditoria
from taller.application.use_cases.comprobantes import (
    ActualizarComprobante,
    ActualizarComprobanteCommand,
    AnularComprobante,
    ComprobarComprobante,
    ListarComprobantes,
    ListarComprobantesQuery,
    ObtenerComprobante,
    PreviewComprobante,
    RegistrarComprobante,
    RegistrarComprobanteCommand,
)
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.enums import ClasificacionComprobante, EstadoComprobante

Financiero = Annotated[Usuario, Depends(require_roles(Rol.ADMIN, Rol.ADMINISTRACION))]

router = APIRouter(prefix="/comprobantes", tags=["comprobantes"])


@router.post("", response_model=ComprobanteResponse, status_code=status.HTTP_201_CREATED)
def registrar_comprobante(
    _: Financiero,
    payload: ComprobanteCreate,
    uc: Annotated[RegistrarComprobante, Depends(uc_registrar_comprobante)],
) -> ComprobanteResponse:
    return ComprobanteResponse.from_domain(
        uc.execute(RegistrarComprobanteCommand(**payload.model_dump()))
    )


@router.get("", response_model=list[ComprobanteResponse])
def listar_comprobantes(
    _: Financiero,
    uc: Annotated[ListarComprobantes, Depends(uc_listar_comprobantes)],
    clasificacion: Annotated[ClasificacionComprobante | None, Query()] = None,
    estado: Annotated[EstadoComprobante | None, Query()] = None,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
) -> list[ComprobanteResponse]:
    query = ListarComprobantesQuery(
        clasificacion=clasificacion, estado=estado, desde=desde, hasta=hasta, q=q
    )
    return [ComprobanteResponse.from_domain(c) for c in uc.execute(query)]


@router.post("/ocr", response_model=OcrPreviewResponse)
async def preview_ocr(
    _: Financiero,
    uc: Annotated[PreviewComprobante, Depends(uc_preview_comprobante)],
    archivo: Annotated[UploadFile, File()],
) -> OcrPreviewResponse:
    contenido = await archivo.read()
    datos = await run_in_threadpool(
        uc.execute,
        contenido=contenido,
        content_type=archivo.content_type or "",
        nombre=archivo.filename or "comprobante",
    )
    return OcrPreviewResponse(**asdict(datos))


@router.get("/{comprobante_id}", response_model=ComprobanteResponse)
def obtener_comprobante(
    comprobante_id: UUID,
    _: Financiero,
    uc: Annotated[ObtenerComprobante, Depends(uc_obtener_comprobante)],
) -> ComprobanteResponse:
    return ComprobanteResponse.from_domain(uc.execute(comprobante_id))


@router.patch("/{comprobante_id}", response_model=ComprobanteResponse)
def actualizar_comprobante(
    comprobante_id: UUID,
    _: Financiero,
    payload: ComprobanteUpdate,
    uc: Annotated[ActualizarComprobante, Depends(uc_actualizar_comprobante)],
) -> ComprobanteResponse:
    cmd = ActualizarComprobanteCommand(comprobante_id=comprobante_id, **payload.model_dump())
    return ComprobanteResponse.from_domain(uc.execute(cmd))


@router.post("/{comprobante_id}/comprobar", response_model=ComprobanteResponse)
def comprobar_comprobante(
    comprobante_id: UUID,
    usuario: Financiero,
    uc: Annotated[ComprobarComprobante, Depends(uc_comprobar_comprobante)],
    audit: Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)],
) -> ComprobanteResponse:
    comprobante = uc.execute(comprobante_id)
    audit.execute(
        usuario,
        accion="comprobar",
        entidad="comprobante",
        entidad_id=comprobante.id,
        detalle=f"{comprobante.tipo.value} #{comprobante.numero or '—'} por {comprobante.total}",
    )
    return ComprobanteResponse.from_domain(comprobante)


@router.post("/{comprobante_id}/anular", response_model=ComprobanteResponse)
def anular_comprobante(
    comprobante_id: UUID,
    usuario: Financiero,
    uc: Annotated[AnularComprobante, Depends(uc_anular_comprobante)],
    audit: Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)],
) -> ComprobanteResponse:
    comprobante = uc.execute(comprobante_id)
    audit.execute(
        usuario,
        accion="anular",
        entidad="comprobante",
        entidad_id=comprobante.id,
        detalle=f"{comprobante.tipo.value} #{comprobante.numero or '—'} por {comprobante.total}",
    )
    return ComprobanteResponse.from_domain(comprobante)

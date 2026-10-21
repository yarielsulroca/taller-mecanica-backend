from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from taller.adapters.inbound.api.deps import require_roles
from taller.adapters.inbound.api.deps_cobros import (
    uc_adjuntar_comprobante,
    uc_listar_adjuntos,
    uc_listar_cobros,
    uc_registrar_cobro,
)
from taller.adapters.inbound.api.deps_finanzas import repo_adjuntos
from taller.adapters.inbound.api.schemas_cobros import AdjuntoResponse, CobroCreate
from taller.adapters.inbound.api.schemas_finanzas import MovimientoResponse
from taller.adapters.outbound.postgres.finanzas_repository import SqlMovimientoAdjuntoRepository
from taller.application.use_cases.cobros import (
    AdjuntarComprobante,
    AdjuntarComprobanteCommand,
    ListarAdjuntos,
    ListarCobros,
    RegistrarCobro,
    RegistrarCobroCommand,
    RetencionCommand,
)
from taller.domain.entities.usuario import Rol, Usuario

Financiero = Annotated[Usuario, Depends(require_roles(Rol.ADMIN, Rol.ADMINISTRACION))]

router = APIRouter(prefix="/cobros", tags=["cobros"])


@router.post("", response_model=MovimientoResponse, status_code=status.HTTP_201_CREATED)
def registrar_cobro(
    _: Financiero,
    payload: CobroCreate,
    uc: Annotated[RegistrarCobro, Depends(uc_registrar_cobro)],
) -> MovimientoResponse:
    datos = payload.model_dump(exclude={"retenciones"})
    # H5: los certificados se convierten a entidades del dominio antes de persistir.
    retenciones = tuple(
        RetencionCommand(tipo=r.tipo, monto=r.monto, certificado=r.certificado)
        for r in payload.retenciones
    )
    return MovimientoResponse.from_domain(
        uc.execute(RegistrarCobroCommand(**datos, retenciones=retenciones))
    )


@router.get("", response_model=list[MovimientoResponse])
def listar_cobros(
    _: Financiero,
    uc: Annotated[ListarCobros, Depends(uc_listar_cobros)],
    adjuntos: Annotated[SqlMovimientoAdjuntoRepository, Depends(repo_adjuntos)],
    cliente_id: Annotated[UUID | None, Query()] = None,
) -> list[MovimientoResponse]:
    cobros = uc.execute(cliente_id=cliente_id)
    conteo = adjuntos.contar([m.id for m in cobros])
    return [MovimientoResponse.from_domain(m, adjuntos=conteo.get(m.id, 0)) for m in cobros]


@router.post(
    "/{movimiento_id}/adjuntos",
    response_model=AdjuntoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def adjuntar_comprobante(
    movimiento_id: UUID,
    usuario: Financiero,
    uc: Annotated[AdjuntarComprobante, Depends(uc_adjuntar_comprobante)],
    archivo: Annotated[UploadFile, File()],
    nota: Annotated[str | None, Form()] = None,
) -> AdjuntoResponse:
    contenido = await archivo.read()
    cmd = AdjuntarComprobanteCommand(
        movimiento_id=movimiento_id,
        nombre_original=archivo.filename or "comprobante",
        contenido=contenido,
        content_type=archivo.content_type or "",
        nota=nota,
        autor_id=usuario.id,
    )
    return AdjuntoResponse.from_domain(uc.execute(cmd))


@router.get("/{movimiento_id}/adjuntos", response_model=list[AdjuntoResponse])
def listar_adjuntos(
    movimiento_id: UUID,
    _: Financiero,
    uc: Annotated[ListarAdjuntos, Depends(uc_listar_adjuntos)],
) -> list[AdjuntoResponse]:
    return [AdjuntoResponse.from_domain(a) for a in uc.execute(movimiento_id)]

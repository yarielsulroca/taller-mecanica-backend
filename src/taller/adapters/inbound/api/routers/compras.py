from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from taller.adapters.inbound.api.deps import require_roles
from taller.adapters.inbound.api.deps_auditoria import uc_registrar_auditoria
from taller.adapters.inbound.api.deps_compras import (
    uc_anular_compra,
    uc_listar_compras,
    uc_obtener_compra,
    uc_pagar_compra,
    uc_registrar_compra,
)
from taller.adapters.inbound.api.schemas_compras import (
    CompraCreate,
    CompraResponse,
    PagoCompraRequest,
)
from taller.application.use_cases.auditoria import RegistrarAuditoria
from taller.application.use_cases.compras import (
    AnularCompra,
    ItemCompraCommand,
    ListarCompras,
    ListarComprasQuery,
    ObtenerCompra,
    RegistrarCompra,
    RegistrarCompraCommand,
    RegistrarPagoCompra,
    RegistrarPagoCompraCommand,
)
from taller.domain.entities.movimiento import Retencion
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.enums import EstadoCompra

Financiero = Annotated[Usuario, Depends(require_roles(Rol.ADMIN, Rol.ADMINISTRACION))]

router = APIRouter(prefix="/compras", tags=["compras"])


@router.post("", response_model=CompraResponse, status_code=status.HTTP_201_CREATED)
def registrar_compra(
    _: Financiero,
    payload: CompraCreate,
    uc: Annotated[RegistrarCompra, Depends(uc_registrar_compra)],
) -> CompraResponse:
    datos = payload.model_dump(exclude={"items"})
    cmd = RegistrarCompraCommand(
        items=tuple(ItemCompraCommand(**item) for item in payload.model_dump()["items"]),
        **datos,
    )
    return CompraResponse.from_domain(uc.execute(cmd))


@router.get("", response_model=list[CompraResponse])
def listar_compras(
    _: Financiero,
    uc: Annotated[ListarCompras, Depends(uc_listar_compras)],
    proveedor_id: Annotated[UUID | None, Query()] = None,
    ot_id: Annotated[UUID | None, Query()] = None,
    estado: Annotated[EstadoCompra | None, Query()] = None,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> list[CompraResponse]:
    query = ListarComprasQuery(
        proveedor_id=proveedor_id, ot_id=ot_id, estado=estado, desde=desde, hasta=hasta
    )
    return [CompraResponse.from_domain(c) for c in uc.execute(query)]


@router.get("/{compra_id}", response_model=CompraResponse)
def obtener_compra(
    compra_id: UUID,
    _: Financiero,
    uc: Annotated[ObtenerCompra, Depends(uc_obtener_compra)],
) -> CompraResponse:
    return CompraResponse.from_domain(uc.execute(compra_id))


@router.post("/{compra_id}/anular", response_model=CompraResponse)
def anular_compra(
    compra_id: UUID,
    usuario: Financiero,
    uc: Annotated[AnularCompra, Depends(uc_anular_compra)],
    audit: Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)],
) -> CompraResponse:
    compra = uc.execute(compra_id)
    audit.execute(
        usuario,
        accion="anular",
        entidad="compra",
        entidad_id=compra.id,
        detalle=f"compra por {compra.total} anulada",
    )
    return CompraResponse.from_domain(compra)


@router.post("/{compra_id}/pagar", response_model=CompraResponse)
def pagar_compra(
    compra_id: UUID,
    _: Financiero,
    payload: PagoCompraRequest,
    uc: Annotated[RegistrarPagoCompra, Depends(uc_pagar_compra)],
) -> CompraResponse:
    datos = payload.model_dump(exclude={"retenciones"})
    retenciones = tuple(
        Retencion(tipo=r.tipo, monto=r.monto, certificado=r.certificado)
        for r in payload.retenciones
    )
    cmd = RegistrarPagoCompraCommand(compra_id=compra_id, **datos, retenciones=retenciones)
    respuesta = CompraResponse.from_domain(uc.execute(cmd))
    respuesta.pago_movimiento_id = cmd.movimiento_id
    return respuesta

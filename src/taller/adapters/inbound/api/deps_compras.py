from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_session
from taller.adapters.inbound.api.deps_finanzas import repo_cuotas, repo_movimientos
from taller.adapters.inbound.api.deps_maestros import repo_proveedores
from taller.adapters.outbound.postgres.compras_repository import SqlCompraRepository
from taller.adapters.outbound.postgres.comprobantes_repository import SqlComprobanteRepository
from taller.adapters.outbound.postgres.configuracion_repository import (
    SqlConfiguracionTallerRepository,
)
from taller.adapters.outbound.postgres.finanzas_repository import (
    SqlCuotaRepository,
    SqlMovimientoRepository,
)
from taller.adapters.outbound.postgres.maestros_repositories import SqlProveedorRepository
from taller.application.use_cases.compras import (
    AnularCompra,
    ListarCompras,
    ObtenerCompra,
    RegistrarCompra,
    RegistrarPagoCompra,
)


def repo_compras(session: Annotated[Session, Depends(get_session)]) -> SqlCompraRepository:
    return SqlCompraRepository(session)


def repo_comprobantes_compras(
    session: Annotated[Session, Depends(get_session)],
) -> SqlComprobanteRepository:
    return SqlComprobanteRepository(session)


def repo_configuracion_compras(
    session: Annotated[Session, Depends(get_session)],
) -> SqlConfiguracionTallerRepository:
    return SqlConfiguracionTallerRepository(session)


def uc_registrar_compra(
    compras: Annotated[SqlCompraRepository, Depends(repo_compras)],
    cuotas: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
    proveedores: Annotated[SqlProveedorRepository, Depends(repo_proveedores)],
    comprobantes: Annotated[SqlComprobanteRepository, Depends(repo_comprobantes_compras)],
    configuracion: Annotated[SqlConfiguracionTallerRepository, Depends(repo_configuracion_compras)],
) -> RegistrarCompra:
    return RegistrarCompra(compras, cuotas, proveedores, comprobantes, configuracion)


def uc_anular_compra(
    compras: Annotated[SqlCompraRepository, Depends(repo_compras)],
    cuotas: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
) -> AnularCompra:
    return AnularCompra(compras, cuotas)


def uc_listar_compras(
    compras: Annotated[SqlCompraRepository, Depends(repo_compras)],
) -> ListarCompras:
    return ListarCompras(compras)


def uc_obtener_compra(
    compras: Annotated[SqlCompraRepository, Depends(repo_compras)],
) -> ObtenerCompra:
    return ObtenerCompra(compras)


def uc_pagar_compra(
    compras: Annotated[SqlCompraRepository, Depends(repo_compras)],
    cuotas: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
) -> RegistrarPagoCompra:
    return RegistrarPagoCompra(compras, cuotas, movimientos)

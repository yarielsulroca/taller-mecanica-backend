from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from taller.adapters.inbound.api.deps import get_container
from taller.adapters.inbound.api.deps_finanzas import (
    repo_adjuntos,
    repo_cuotas,
    repo_movimientos,
    uc_adjuntar_comprobante,
    uc_listar_adjuntos,
)
from taller.adapters.inbound.api.deps_maestros import repo_clientes
from taller.adapters.inbound.api.deps_ordenes import cobranza_ot
from taller.adapters.outbound.postgres.finanzas_repository import (
    SqlCuotaRepository,
    SqlMovimientoAdjuntoRepository,
    SqlMovimientoRepository,
)
from taller.adapters.outbound.postgres.maestros_repositories import SqlClienteRepository
from taller.application.use_cases.cobranza_ot import CobranzaOT
from taller.application.use_cases.cobros import (
    ListarCobros,
    RegistrarCobro,
)
from taller.container import Container

__all__ = [
    "uc_adjuntar_comprobante",
    "uc_listar_adjuntos",
    "uc_listar_cobros",
    "uc_registrar_cobro",
]


def uc_registrar_cobro(
    clientes: Annotated[SqlClienteRepository, Depends(repo_clientes)],
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    cuotas: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
    adjuntos: Annotated[SqlMovimientoAdjuntoRepository, Depends(repo_adjuntos)],
    container: Annotated[Container, Depends(get_container)],
    cobranza: Annotated[CobranzaOT, Depends(cobranza_ot)],
) -> RegistrarCobro:
    return RegistrarCobro(
        clientes, movimientos, cuotas, adjuntos, container.storage, container.clock, cobranza
    )


def uc_listar_cobros(
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
) -> ListarCobros:
    return ListarCobros(movimientos)

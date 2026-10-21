from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from taller.adapters.inbound.api.deps import get_container, require_roles
from taller.adapters.inbound.api.deps_vencimientos import (
    uc_actualizar_gasto_fijo,
    uc_archivar_gasto_fijo,
    uc_crear_gasto_fijo,
    uc_ejecutar_vencimientos,
    uc_liquidar_sueldo,
    uc_listar_gastos_fijos,
    uc_listar_obligaciones,
    uc_omitir_obligacion,
    uc_pagar_gasto_fijo,
)
from taller.adapters.inbound.api.schemas_vencimientos import (
    GastoFijoPayload,
    GastoFijoResponse,
    LiquidarSueldoPayload,
    ObligacionResponse,
    OmitirPayload,
    PagarGastoPayload,
    RevisionResponse,
)
from taller.application.use_cases.vencimientos import (
    ActualizarGastoFijo,
    ArchivarGastoFijo,
    CrearGastoFijo,
    EjecutarVencimientos,
    GastoFijoCommand,
    LiquidarSueldo,
    LiquidarSueldoCommand,
    ListarGastosFijos,
    ListarObligaciones,
    OmitirObligacion,
    PagarGastoFijo,
    PagarGastoFijoCommand,
)
from taller.container import Container
from taller.domain.calendario import fecha_argentina
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.entities.vencimiento import Obligacion
from taller.domain.enums import EstadoObligacion

Financiero = Annotated[Usuario, Depends(require_roles(Rol.ADMIN, Rol.ADMINISTRACION))]
Contenedor = Annotated[Container, Depends(get_container)]

router = APIRouter(prefix="/vencimientos", tags=["vencimientos"])


def _respuesta(o: Obligacion, container: Container) -> ObligacionResponse:
    return ObligacionResponse.from_domain(o, fecha_argentina(container.clock.ahora()))


@router.get("/gastos-fijos", response_model=list[GastoFijoResponse])
def listar_gastos_fijos(
    _: Financiero,
    uc: Annotated[ListarGastosFijos, Depends(uc_listar_gastos_fijos)],
    incluir_archivados: Annotated[bool, Query()] = False,
) -> list[GastoFijoResponse]:
    return [GastoFijoResponse.from_domain(g) for g in uc.execute(incluir_archivados)]


@router.post("/gastos-fijos", response_model=GastoFijoResponse, status_code=status.HTTP_201_CREATED)
def crear_gasto_fijo(
    _: Financiero,
    payload: GastoFijoPayload,
    uc: Annotated[CrearGastoFijo, Depends(uc_crear_gasto_fijo)],
) -> GastoFijoResponse:
    return GastoFijoResponse.from_domain(uc.execute(GastoFijoCommand(**payload.model_dump())))


@router.patch("/gastos-fijos/{gasto_id}", response_model=GastoFijoResponse)
def actualizar_gasto_fijo(
    gasto_id: UUID,
    _: Financiero,
    payload: GastoFijoPayload,
    uc: Annotated[ActualizarGastoFijo, Depends(uc_actualizar_gasto_fijo)],
) -> GastoFijoResponse:
    cmd = GastoFijoCommand(**payload.model_dump())
    return GastoFijoResponse.from_domain(uc.execute(gasto_id, cmd))


@router.post("/gastos-fijos/{gasto_id}/archivar", response_model=GastoFijoResponse)
def archivar_gasto_fijo(
    gasto_id: UUID,
    _: Financiero,
    uc: Annotated[ArchivarGastoFijo, Depends(uc_archivar_gasto_fijo)],
) -> GastoFijoResponse:
    return GastoFijoResponse.from_domain(uc.execute(gasto_id))


@router.post("/revisar", response_model=RevisionResponse)
def revisar(
    _: Financiero,
    uc: Annotated[EjecutarVencimientos, Depends(uc_ejecutar_vencimientos)],
) -> RevisionResponse:
    r = uc.execute()
    return RevisionResponse(generadas=r.generadas, resueltas=r.resueltas, avisos=r.avisos)


@router.get("", response_model=list[ObligacionResponse])
def listar_obligaciones(
    _: Financiero,
    container: Contenedor,
    uc: Annotated[ListarObligaciones, Depends(uc_listar_obligaciones)],
    estado: Annotated[EstadoObligacion | None, Query()] = None,
) -> list[ObligacionResponse]:
    return [_respuesta(o, container) for o in uc.execute(estado)]


@router.post("/{obligacion_id}/pagar", response_model=ObligacionResponse)
def pagar_gasto(
    obligacion_id: UUID,
    _: Financiero,
    payload: PagarGastoPayload,
    container: Contenedor,
    uc: Annotated[PagarGastoFijo, Depends(uc_pagar_gasto_fijo)],
) -> ObligacionResponse:
    cmd = PagarGastoFijoCommand(**payload.model_dump())
    return _respuesta(uc.execute(obligacion_id, cmd), container)


@router.post("/{obligacion_id}/liquidar", response_model=ObligacionResponse)
def liquidar_sueldo(
    obligacion_id: UUID,
    _: Financiero,
    payload: LiquidarSueldoPayload,
    container: Contenedor,
    uc: Annotated[LiquidarSueldo, Depends(uc_liquidar_sueldo)],
) -> ObligacionResponse:
    cmd = LiquidarSueldoCommand(**payload.model_dump())
    return _respuesta(uc.execute(obligacion_id, cmd), container)


@router.post("/{obligacion_id}/omitir", response_model=ObligacionResponse)
def omitir(
    obligacion_id: UUID,
    _: Financiero,
    payload: OmitirPayload,
    container: Contenedor,
    uc: Annotated[OmitirObligacion, Depends(uc_omitir_obligacion)],
) -> ObligacionResponse:
    return _respuesta(uc.execute(obligacion_id, payload.motivo), container)

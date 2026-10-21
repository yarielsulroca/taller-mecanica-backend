from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from taller.adapters.inbound.api.deps import require_roles
from taller.adapters.inbound.api.deps_pagos import (
    uc_anular_adelanto,
    uc_liquidar_trabajador,
    uc_listar_adelantos,
    uc_listar_liquidaciones,
    uc_registrar_adelanto,
    uc_registrar_gasto,
    uc_sugerir_liquidacion,
)
from taller.adapters.inbound.api.schemas_finanzas import MovimientoResponse
from taller.adapters.inbound.api.schemas_pagos import (
    AdelantoCreate,
    AdelantoResponse,
    GastoCreate,
    LiquidacionCreate,
    LiquidacionResponse,
    SugerenciaLiquidacionResponse,
)
from taller.application.use_cases.pagos import (
    AnularAdelanto,
    LiquidarTrabajador,
    LiquidarTrabajadorCommand,
    ListarAdelantos,
    ListarAdelantosQuery,
    ListarLiquidaciones,
    RegistrarAdelanto,
    RegistrarAdelantoCommand,
    RegistrarGasto,
    RegistrarGastoCommand,
    SugerirLiquidacion,
)
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.enums import EstadoAdelanto

Financiero = Annotated[Usuario, Depends(require_roles(Rol.ADMIN, Rol.ADMINISTRACION))]

router = APIRouter(prefix="/pagos", tags=["pagos"])


@router.post("/adelantos", response_model=AdelantoResponse, status_code=status.HTTP_201_CREATED)
def registrar_adelanto(
    _: Financiero,
    payload: AdelantoCreate,
    uc: Annotated[RegistrarAdelanto, Depends(uc_registrar_adelanto)],
) -> AdelantoResponse:
    cmd = RegistrarAdelantoCommand(**payload.model_dump())
    return AdelantoResponse.from_domain(uc.execute(cmd))


@router.get("/adelantos", response_model=list[AdelantoResponse])
def listar_adelantos(
    _: Financiero,
    uc: Annotated[ListarAdelantos, Depends(uc_listar_adelantos)],
    trabajador_id: Annotated[UUID | None, Query()] = None,
    estado: Annotated[EstadoAdelanto | None, Query()] = None,
) -> list[AdelantoResponse]:
    query = ListarAdelantosQuery(trabajador_id=trabajador_id, estado=estado)
    return [AdelantoResponse.from_domain(a) for a in uc.execute(query)]


@router.post("/adelantos/{adelanto_id}/anular", response_model=AdelantoResponse)
def anular_adelanto(
    adelanto_id: UUID,
    _: Financiero,
    uc: Annotated[AnularAdelanto, Depends(uc_anular_adelanto)],
) -> AdelantoResponse:
    return AdelantoResponse.from_domain(uc.execute(adelanto_id))


@router.post(
    "/liquidaciones", response_model=LiquidacionResponse, status_code=status.HTTP_201_CREATED
)
def liquidar_trabajador(
    _: Financiero,
    payload: LiquidacionCreate,
    uc: Annotated[LiquidarTrabajador, Depends(uc_liquidar_trabajador)],
) -> LiquidacionResponse:
    return LiquidacionResponse.from_domain(
        uc.execute(LiquidarTrabajadorCommand(**payload.model_dump()))
    )


@router.get("/liquidaciones/sugerencia", response_model=SugerenciaLiquidacionResponse)
def sugerir_liquidacion(
    _: Financiero,
    uc: Annotated[SugerirLiquidacion, Depends(uc_sugerir_liquidacion)],
    trabajador_id: Annotated[UUID, Query()],
    desde: Annotated[date, Query()],
    hasta: Annotated[date, Query()],
    horas: Annotated[Decimal | None, Query(ge=0)] = None,
) -> SugerenciaLiquidacionResponse:
    return SugerenciaLiquidacionResponse.from_domain(uc.execute(trabajador_id, desde, hasta, horas))


@router.get("/liquidaciones", response_model=list[LiquidacionResponse])
def listar_liquidaciones(
    _: Financiero,
    uc: Annotated[ListarLiquidaciones, Depends(uc_listar_liquidaciones)],
    trabajador_id: Annotated[UUID | None, Query()] = None,
) -> list[LiquidacionResponse]:
    return [LiquidacionResponse.from_domain(liq) for liq in uc.execute(trabajador_id)]


@router.post("/gastos", response_model=MovimientoResponse, status_code=status.HTTP_201_CREATED)
def registrar_gasto(
    _: Financiero,
    payload: GastoCreate,
    uc: Annotated[RegistrarGasto, Depends(uc_registrar_gasto)],
) -> MovimientoResponse:
    return MovimientoResponse.from_domain(uc.execute(RegistrarGastoCommand(**payload.model_dump())))

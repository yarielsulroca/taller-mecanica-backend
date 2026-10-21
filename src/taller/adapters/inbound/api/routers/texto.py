from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from taller.adapters.inbound.api.deps import get_current_user
from taller.adapters.inbound.api.deps_texto import (
    uc_corregir_texto,
    uc_registrar_terminos,
    uc_sugerir_terminos,
)
from taller.adapters.inbound.api.schemas_texto import (
    CorreccionPalabraResponse,
    CorreccionResponse,
    CorregirTextoRequest,
    RegistrarTextoRequest,
    SugerenciasResponse,
)
from taller.application.use_cases.texto import (
    CorregirTexto,
    RegistrarTerminosDeTexto,
    SugerirTerminos,
)
from taller.domain.entities.usuario import Usuario

Autenticado = Annotated[Usuario, Depends(get_current_user)]

router = APIRouter(prefix="/texto", tags=["texto"])


@router.get("/sugerencias", response_model=SugerenciasResponse)
def sugerencias(
    _: Autenticado,
    uc: Annotated[SugerirTerminos, Depends(uc_sugerir_terminos)],
    q: Annotated[str, Query(min_length=2)],
    limite: Annotated[int, Query(ge=1, le=25)] = 10,
) -> SugerenciasResponse:
    return SugerenciasResponse(sugerencias=uc.execute(q, limite))


@router.post("/corregir", response_model=CorreccionResponse)
def corregir(
    _: Autenticado,
    payload: CorregirTextoRequest,
    uc: Annotated[CorregirTexto, Depends(uc_corregir_texto)],
) -> CorreccionResponse:
    resultado = uc.execute(payload.texto)
    return CorreccionResponse(
        palabras=[
            CorreccionPalabraResponse(palabra=p.palabra, sugerencias=p.sugerencias)
            for p in resultado.palabras
        ]
    )


@router.post("/registrar", status_code=204)
def registrar(
    _: Autenticado,
    payload: RegistrarTextoRequest,
    uc: Annotated[RegistrarTerminosDeTexto, Depends(uc_registrar_terminos)],
) -> None:
    uc.execute(payload.texto)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from taller.adapters.inbound.api.deps import get_autenticar_usuario, get_current_user
from taller.adapters.inbound.api.schemas import LoginRequest, TokenResponse, UsuarioResponse
from taller.application.dto.auth import AutenticarCommand
from taller.application.use_cases.autenticar_usuario import AutenticarUsuario
from taller.domain.entities.usuario import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])


def _a_response(usuario: Usuario) -> UsuarioResponse:
    return UsuarioResponse(
        id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        roles=sorted(r.value for r in usuario.roles),
        trabajador_id=usuario.trabajador_id,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    use_case: Annotated[AutenticarUsuario, Depends(get_autenticar_usuario)],
) -> TokenResponse:
    resultado = use_case.execute(
        AutenticarCommand(email=str(payload.email), password=payload.password)
    )
    return TokenResponse(
        access_token=resultado.token,
        usuario=_a_response(resultado.usuario),
    )


@router.get("/me", response_model=UsuarioResponse)
def me(usuario: Annotated[Usuario, Depends(get_current_user)]) -> UsuarioResponse:
    return _a_response(usuario)

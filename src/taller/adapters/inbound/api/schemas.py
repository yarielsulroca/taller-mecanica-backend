from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str


class UsuarioResponse(BaseModel):
    id: UUID
    nombre: str
    email: str
    roles: list[str]
    trabajador_id: UUID | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse

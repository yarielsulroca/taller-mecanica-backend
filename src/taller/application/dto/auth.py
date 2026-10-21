from __future__ import annotations

from dataclasses import dataclass

from taller.domain.entities.usuario import Usuario


@dataclass(frozen=True, slots=True)
class AutenticarCommand:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class AutenticadoResult:
    token: str
    usuario: Usuario

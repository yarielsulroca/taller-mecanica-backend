from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from taller.domain.entities.usuario import Usuario
from taller.domain.exceptions import TokenInvalido


class JwtTokenService:
    """Emite y valida tokens JWT (HS256)."""

    def __init__(self, secret: str, algorithm: str = "HS256", minutos: int = 60) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._minutos = minutos

    def emitir(self, usuario: Usuario) -> str:
        ahora = datetime.now(UTC)
        payload: dict[str, object] = {
            "sub": str(usuario.id),
            "email": usuario.email,
            "roles": sorted(r.value for r in usuario.roles),
            "iat": ahora,
            "exp": ahora + timedelta(minutes=self._minutos),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decodificar(self, token: str) -> dict[str, object]:
        try:
            return jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise TokenInvalido("Token inválido o vencido") from exc

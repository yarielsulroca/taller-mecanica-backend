from __future__ import annotations

from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2PasswordHasher:
    """Hash de contraseñas con argon2id (skill taller-security)."""

    def __init__(self) -> None:
        self._hasher = _Argon2()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verificar(self, password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

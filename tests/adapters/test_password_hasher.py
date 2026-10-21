from __future__ import annotations

from taller.adapters.outbound.security.password_hasher import Argon2PasswordHasher


def test_hash_y_verificacion() -> None:
    hasher = Argon2PasswordHasher()
    h = hasher.hash("secreto-123")
    assert h != "secreto-123"
    assert hasher.verificar("secreto-123", h)
    assert not hasher.verificar("otro", h)


def test_verificacion_con_hash_invalido_no_explota() -> None:
    hasher = Argon2PasswordHasher()
    assert not hasher.verificar("x", "no-es-un-hash")

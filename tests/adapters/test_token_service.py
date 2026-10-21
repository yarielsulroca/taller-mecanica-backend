from __future__ import annotations

import pytest

from taller.adapters.outbound.security.token_service import JwtTokenService
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.exceptions import TokenInvalido


def _usuario() -> Usuario:
    return Usuario.crear(
        nombre="A", email="a@x.com", password_hash="x", roles={Rol.ADMIN, Rol.MECANICO}
    )


def test_emite_y_decodifica() -> None:
    servicio = JwtTokenService("secreto-de-prueba-con-32-bytes-ok", minutos=5)
    token = servicio.emitir(_usuario())
    payload = servicio.decodificar(token)
    assert payload["email"] == "a@x.com"
    assert payload["roles"] == ["admin", "mecanico"]


def test_token_invalido_falla() -> None:
    servicio = JwtTokenService("secreto-de-prueba-con-32-bytes-ok", minutos=5)
    with pytest.raises(TokenInvalido):
        servicio.decodificar("esto.no.es.un.jwt")


def test_token_con_otra_clave_falla() -> None:
    emisor = JwtTokenService("secreto-de-prueba-con-32-bytes-ok", minutos=5)
    validador = JwtTokenService("otro-secreto-de-prueba-32-bytes-xx", minutos=5)
    with pytest.raises(TokenInvalido):
        validador.decodificar(emisor.emitir(_usuario()))

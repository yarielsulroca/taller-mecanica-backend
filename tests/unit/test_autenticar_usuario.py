from __future__ import annotations

import pytest

from taller.application.dto.auth import AutenticarCommand
from taller.application.use_cases.autenticar_usuario import AutenticarUsuario
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.exceptions import CredencialesInvalidas, UsuarioInactivo
from tests.fakes import FakeClock, FakePasswordHasher, FakeTokenService, FakeUsuarioRepository


def _usuario(activo: bool = True) -> Usuario:
    return Usuario.crear(
        nombre="Mecánico",
        email="mecanico@taller.local",
        password_hash="fake$secreto",
        roles={Rol.MECANICO},
        activo=activo,
    )


def _use_case(repo: FakeUsuarioRepository) -> AutenticarUsuario:
    return AutenticarUsuario(repo, FakePasswordHasher(), FakeTokenService(), FakeClock())


def test_login_correcto_emite_token_y_registra_acceso() -> None:
    usuario = _usuario()
    repo = FakeUsuarioRepository([usuario])
    resultado = _use_case(repo).execute(
        AutenticarCommand(email="MECANICO@taller.local", password="secreto")
    )
    assert resultado.token == f"token-{usuario.id}"
    assert resultado.usuario.ultimo_acceso is not None


def test_password_incorrecta_falla() -> None:
    repo = FakeUsuarioRepository([_usuario()])
    with pytest.raises(CredencialesInvalidas):
        _use_case(repo).execute(AutenticarCommand(email="mecanico@taller.local", password="malo"))


def test_usuario_inexistente_falla() -> None:
    repo = FakeUsuarioRepository([])
    with pytest.raises(CredencialesInvalidas):
        _use_case(repo).execute(AutenticarCommand(email="nadie@x.com", password="x"))


def test_usuario_inactivo_falla() -> None:
    repo = FakeUsuarioRepository([_usuario(activo=False)])
    with pytest.raises(UsuarioInactivo):
        _use_case(repo).execute(
            AutenticarCommand(email="mecanico@taller.local", password="secreto")
        )

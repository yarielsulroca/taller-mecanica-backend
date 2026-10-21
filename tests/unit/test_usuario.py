from __future__ import annotations

import pytest

from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.exceptions import SolicitudInvalida


def test_crear_normaliza_email_y_nombre() -> None:
    usuario = Usuario.crear(
        nombre="  Ana  ",
        email="ANA@Taller.Local",
        password_hash="x",
        roles={Rol.ADMINISTRACION},
    )
    assert usuario.email == "ana@taller.local"
    assert usuario.nombre == "Ana"


def test_puede_segun_rol_y_estado() -> None:
    admin = Usuario.crear(nombre="A", email="a@x.com", password_hash="x", roles={Rol.ADMIN})
    assert admin.puede(Rol.ADMIN)
    assert not admin.puede(Rol.MECANICO)

    inactivo = Usuario.crear(
        nombre="B", email="b@x.com", password_hash="x", roles={Rol.ADMIN}, activo=False
    )
    assert not inactivo.puede(Rol.ADMIN)


def test_varios_roles_suman_permisos() -> None:
    usuario = Usuario.crear(
        nombre="C", email="c@x.com", password_hash="x", roles={Rol.MECANICO, Rol.JEFE_TALLER}
    )
    assert usuario.puede(Rol.JEFE_TALLER)
    assert usuario.puede(Rol.MECANICO)
    assert not usuario.puede(Rol.ADMIN, Rol.ADMINISTRACION)


def test_sin_roles_es_invalido() -> None:
    with pytest.raises(SolicitudInvalida):
        Usuario.crear(nombre="D", email="d@x.com", password_hash="x", roles=set())

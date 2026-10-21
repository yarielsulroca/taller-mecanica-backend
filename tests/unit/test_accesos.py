from __future__ import annotations

from decimal import Decimal

import pytest

from taller.application.use_cases.accesos import DefinirAcceso, DefinirAccesoCommand
from taller.application.use_cases.trabajadores import ArchivarTrabajador
from taller.domain.entities.trabajador import Trabajador
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.enums import TipoRemuneracion
from taller.domain.exceptions import Duplicado, SolicitudInvalida, UltimoAdmin
from tests.fakes import FakeClock, FakePasswordHasher, FakeUsuarioRepository
from tests.fakes_maestros import FakeTrabajadorRepository


def _trabajador(nombre: str = "Juan Pérez") -> Trabajador:
    return Trabajador(
        nombre=nombre,
        rol="mecanico",
        tipo_remuneracion=TipoRemuneracion.SUELDO,
        monto_periodo=Decimal("400000"),
    )


def _armar(
    *usuarios: Usuario, trabajador: Trabajador | None = None
) -> tuple[DefinirAcceso, FakeUsuarioRepository, Trabajador]:
    t = trabajador or _trabajador()
    repo = FakeUsuarioRepository(list(usuarios))
    return DefinirAcceso(FakeTrabajadorRepository([t]), repo, FakePasswordHasher()), repo, t


def _admin_suelto() -> Usuario:
    return Usuario.crear(
        nombre="Admin", email="admin@taller.com.ar", password_hash="fake$x", roles={Rol.ADMIN}
    )


def test_habilitar_crea_usuario_con_varios_roles() -> None:
    uc, repo, t = _armar(_admin_suelto())
    usuario = uc.execute(
        DefinirAccesoCommand(
            trabajador_id=t.id,
            habilitado=True,
            email="Juan@Taller.com.ar",
            password="clave-segura",
            roles=frozenset({Rol.MECANICO, Rol.JEFE_TALLER}),
        )
    )
    assert usuario is not None
    assert usuario.email == "juan@taller.com.ar"
    assert usuario.roles == {Rol.MECANICO, Rol.JEFE_TALLER}
    assert usuario.trabajador_id == t.id
    assert usuario.nombre == "Juan Pérez"
    assert repo.obtener_por_trabajador(t.id) is not None


def test_alta_exige_password_y_roles() -> None:
    uc, _, t = _armar()
    with pytest.raises(SolicitudInvalida):
        uc.execute(
            DefinirAccesoCommand(
                trabajador_id=t.id,
                habilitado=True,
                email="a@x.com",
                roles=frozenset({Rol.MECANICO}),
            )
        )
    with pytest.raises(SolicitudInvalida):
        uc.execute(
            DefinirAccesoCommand(
                trabajador_id=t.id, habilitado=True, email="a@x.com", password="clave-segura"
            )
        )


def test_password_corta_rechazada() -> None:
    uc, _, t = _armar()
    with pytest.raises(SolicitudInvalida):
        uc.execute(
            DefinirAccesoCommand(
                trabajador_id=t.id,
                habilitado=True,
                email="a@x.com",
                password="corta",
                roles=frozenset({Rol.MECANICO}),
            )
        )


def test_editar_roles_sin_cambiar_password() -> None:
    uc, repo, t = _armar(_admin_suelto())
    base = DefinirAccesoCommand(
        trabajador_id=t.id,
        habilitado=True,
        email="juan@taller.com.ar",
        password="clave-segura",
        roles=frozenset({Rol.MECANICO}),
    )
    uc.execute(base)
    uc.execute(
        DefinirAccesoCommand(
            trabajador_id=t.id,
            habilitado=True,
            email="juan@taller.com.ar",
            roles=frozenset({Rol.MECANICO, Rol.RECEPCION}),
        )
    )
    usuario = repo.obtener_por_trabajador(t.id)
    assert usuario is not None
    assert usuario.roles == {Rol.MECANICO, Rol.RECEPCION}
    assert usuario.password_hash == "fake$clave-segura"


def test_deshabilitar_desactiva_sin_borrar() -> None:
    uc, repo, t = _armar(_admin_suelto())
    uc.execute(
        DefinirAccesoCommand(
            trabajador_id=t.id,
            habilitado=True,
            email="juan@taller.com.ar",
            password="clave-segura",
            roles=frozenset({Rol.MECANICO}),
        )
    )
    uc.execute(DefinirAccesoCommand(trabajador_id=t.id, habilitado=False))
    usuario = repo.obtener_por_trabajador(t.id)
    assert usuario is not None
    assert usuario.activo is False


def test_email_de_otra_persona_es_duplicado() -> None:
    otro = _trabajador("Otro")
    uc, repo, t = _armar(_admin_suelto())
    repo.guardar(
        Usuario.crear(
            nombre="Otro",
            email="otro@taller.com.ar",
            password_hash="fake$x",
            roles={Rol.MECANICO},
            trabajador_id=otro.id,
        )
    )
    with pytest.raises(Duplicado):
        uc.execute(
            DefinirAccesoCommand(
                trabajador_id=t.id,
                habilitado=True,
                email="otro@taller.com.ar",
                password="clave-segura",
                roles=frozenset({Rol.MECANICO}),
            )
        )


def test_cuenta_existente_sin_trabajador_se_vincula() -> None:
    admin = _admin_suelto()
    uc, repo, t = _armar(admin)
    usuario = uc.execute(
        DefinirAccesoCommand(
            trabajador_id=t.id,
            habilitado=True,
            email="admin@taller.com.ar",
            roles=frozenset({Rol.ADMIN, Rol.JEFE_TALLER}),
        )
    )
    assert usuario is not None
    assert usuario.id == admin.id
    assert usuario.trabajador_id == t.id
    assert usuario.password_hash == "fake$x"


def test_ultimo_admin_no_pierde_el_acceso_ni_el_rol() -> None:
    t = _trabajador()
    admin = Usuario.crear(
        nombre="Dueño",
        email="duenio@taller.com.ar",
        password_hash="fake$x",
        roles={Rol.ADMIN},
        trabajador_id=t.id,
    )
    uc, _, _ = _armar(admin, trabajador=t)
    with pytest.raises(UltimoAdmin):
        uc.execute(DefinirAccesoCommand(trabajador_id=t.id, habilitado=False))
    with pytest.raises(UltimoAdmin):
        uc.execute(
            DefinirAccesoCommand(
                trabajador_id=t.id,
                habilitado=True,
                email="duenio@taller.com.ar",
                roles=frozenset({Rol.MECANICO}),
            )
        )


def test_archivar_trabajador_le_quita_el_acceso() -> None:
    t = _trabajador()
    repo = FakeUsuarioRepository(
        [
            _admin_suelto(),
            Usuario.crear(
                nombre="Juan",
                email="juan@taller.com.ar",
                password_hash="fake$x",
                roles={Rol.MECANICO},
                trabajador_id=t.id,
            ),
        ]
    )
    ArchivarTrabajador(FakeTrabajadorRepository([t]), FakeClock(), repo).execute(t.id)
    usuario = repo.obtener_por_trabajador(t.id)
    assert usuario is not None
    assert usuario.activo is False


def test_trabajador_archivado_no_puede_habilitarse() -> None:
    t = _trabajador()
    t.archivar(FakeClock().ahora())
    uc, _, _ = _armar(trabajador=t)
    with pytest.raises(SolicitudInvalida):
        uc.execute(
            DefinirAccesoCommand(
                trabajador_id=t.id,
                habilitado=True,
                email="a@x.com",
                password="clave-segura",
                roles=frozenset({Rol.MECANICO}),
            )
        )

from __future__ import annotations

from uuid import uuid4

from taller.application.use_cases.auditoria import (
    ConsultarAuditoria,
    ConsultarAuditoriaQuery,
    RegistrarAuditoria,
)
from taller.domain.entities.usuario import Rol, Usuario
from tests.fakes import FakeClock


class FakeAuditoriaRepository:
    """Append-only en memoria."""

    def __init__(self) -> None:
        self._items: list[object] = []

    def guardar(self, registro) -> None:
        self._items.append(registro)

    def listar(self, **filtros):
        items = list(self._items)
        if filtros.get("entidad"):
            items = [a for a in items if a.entidad == filtros["entidad"]]
        if filtros.get("entidad_id"):
            items = [a for a in items if a.entidad_id == filtros["entidad_id"]]
        if filtros.get("usuario_id"):
            items = [a for a in items if a.usuario_id == filtros["usuario_id"]]
        return items


def _usuario(rol: Rol = Rol.ADMIN) -> Usuario:
    return Usuario(
        id=uuid4(),
        nombre="Admin Test",
        email="admin@test.com.ar",
        roles={rol},
        password_hash="x",
    )


def test_registrar_y_consultar() -> None:
    repo = FakeAuditoriaRepository()
    uc = RegistrarAuditoria(repo, FakeClock())
    usuario = _usuario()
    entidad_id = uuid4()
    uc.execute(
        usuario,
        accion="anular",
        entidad="comprobante",
        entidad_id=entidad_id,
        detalle="factura C #12",
    )
    registros = ConsultarAuditoria(repo).execute(
        ConsultarAuditoriaQuery(entidad="comprobante")
    )
    assert len(registros) == 1
    assert registros[0].usuario_nombre == "Admin Test"
    assert registros[0].accion == "anular"
    assert registros[0].entidad_id == entidad_id
    assert registros[0].fecha is not None  # el clock selló el momento


def test_filtro_por_entidad_y_usuario() -> None:
    repo = FakeAuditoriaRepository()
    uc = RegistrarAuditoria(repo, FakeClock())
    admin = _usuario()
    otro = _usuario(Rol.JEFE_TALLER)
    uc.execute(
        admin,
        accion="anular",
        entidad="comprobante",
        entidad_id=uuid4(),
    )
    uc.execute(otro, accion="validar", entidad="orden_trabajo", entidad_id=uuid4())
    assert (
        len(
            ConsultarAuditoria(repo).execute(ConsultarAuditoriaQuery(entidad="comprobante"))
        )
        == 1
    )
    assert (
        len(
            ConsultarAuditoria(repo).execute(
                ConsultarAuditoriaQuery(usuario_id=admin.id)
            )
        )
        == 1
    )
    total = ConsultarAuditoria(repo).execute(ConsultarAuditoriaQuery())
    assert len(total) == 2
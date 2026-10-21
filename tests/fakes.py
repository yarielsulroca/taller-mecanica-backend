from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from taller.domain.entities.usuario import Usuario


class FakeUsuarioRepository:
    def __init__(self, usuarios: list[Usuario] | None = None) -> None:
        self._usuarios: dict[UUID, Usuario] = {u.id: replace(u) for u in (usuarios or [])}

    def obtener_por_email(self, email: str) -> Usuario | None:
        return next((replace(u) for u in self._usuarios.values() if u.email == email), None)

    def obtener_por_id(self, usuario_id: UUID) -> Usuario | None:
        usuario = self._usuarios.get(usuario_id)
        return replace(usuario) if usuario else None

    def obtener_por_trabajador(self, trabajador_id: UUID) -> Usuario | None:
        return next(
            (replace(u) for u in self._usuarios.values() if u.trabajador_id == trabajador_id),
            None,
        )

    def listar_vinculados(self) -> list[Usuario]:
        return [replace(u) for u in self._usuarios.values() if u.trabajador_id is not None]

    def contar_admins_activos(self) -> int:
        return sum(1 for u in self._usuarios.values() if u.es_admin_activo)

    def guardar(self, usuario: Usuario) -> None:
        self._usuarios[usuario.id] = replace(usuario)


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"fake${password}"

    def verificar(self, password: str, password_hash: str) -> bool:
        return password_hash == f"fake${password}"


class FakeTokenService:
    def emitir(self, usuario: Usuario) -> str:
        return f"token-{usuario.id}"

    def decodificar(self, token: str) -> dict[str, object]:
        return {"sub": token.removeprefix("token-")}


class FakeClock:
    def __init__(self, momento: datetime | None = None) -> None:
        self._momento = momento or datetime(2026, 10, 6, 12, 0, tzinfo=UTC)

    def ahora(self) -> datetime:
        return self._momento

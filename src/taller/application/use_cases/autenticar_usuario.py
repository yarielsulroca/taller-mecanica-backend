from __future__ import annotations

from taller.application.dto.auth import AutenticadoResult, AutenticarCommand
from taller.domain.exceptions import CredencialesInvalidas, UsuarioInactivo
from taller.domain.ports import Clock, PasswordHasher, TokenService, UsuarioRepository


class AutenticarUsuario:
    """Valida credenciales y emite un token (UC-001)."""

    def __init__(
        self,
        usuarios: UsuarioRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        clock: Clock,
    ) -> None:
        self._usuarios = usuarios
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock

    def execute(self, cmd: AutenticarCommand) -> AutenticadoResult:
        usuario = self._usuarios.obtener_por_email(cmd.email.strip().lower())
        if usuario is None or not self._hasher.verificar(cmd.password, usuario.password_hash):
            raise CredencialesInvalidas("Email o contraseña incorrectos")
        if not usuario.activo:
            raise UsuarioInactivo("El usuario está inactivo")

        usuario.ultimo_acceso = self._clock.ahora()
        self._usuarios.guardar(usuario)
        return AutenticadoResult(token=self._tokens.emitir(usuario), usuario=usuario)

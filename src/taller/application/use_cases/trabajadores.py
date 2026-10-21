from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from taller.application.use_cases.accesos import revocar_acceso
from taller.domain.entities.trabajador import Trabajador
from taller.domain.enums import PeriodicidadPago, TipoRemuneracion
from taller.domain.exceptions import NoEncontrado
from taller.domain.ports import Clock, UsuarioRepository
from taller.domain.ports.repositories import TrabajadorRepository


@dataclass(frozen=True, slots=True)
class CrearTrabajadorCommand:
    nombre: str
    rol: str
    tipo_remuneracion: TipoRemuneracion
    periodicidad_pago: PeriodicidadPago = PeriodicidadPago.MENSUAL
    monto_periodo: Decimal | None = None
    valor_hora: Decimal | None = None
    porcentaje_comision: Decimal | None = None


class CrearTrabajador:
    def __init__(self, repo: TrabajadorRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CrearTrabajadorCommand) -> Trabajador:
        trabajador = Trabajador(
            nombre=cmd.nombre.strip(),
            rol=cmd.rol,
            tipo_remuneracion=cmd.tipo_remuneracion,
            periodicidad_pago=cmd.periodicidad_pago,
            monto_periodo=cmd.monto_periodo,
            valor_hora=cmd.valor_hora,
            porcentaje_comision=cmd.porcentaje_comision,
        )
        self._repo.guardar(trabajador)
        return trabajador


@dataclass(frozen=True, slots=True)
class ActualizarTrabajadorCommand:
    trabajador_id: UUID
    nombre: str
    rol: str
    tipo_remuneracion: TipoRemuneracion
    periodicidad_pago: PeriodicidadPago = PeriodicidadPago.MENSUAL
    monto_periodo: Decimal | None = None
    valor_hora: Decimal | None = None
    porcentaje_comision: Decimal | None = None


class ActualizarTrabajador:
    def __init__(self, repo: TrabajadorRepository) -> None:
        self._repo = repo

    def execute(self, cmd: ActualizarTrabajadorCommand) -> Trabajador:
        trabajador = self._repo.obtener(cmd.trabajador_id)
        if trabajador is None:
            raise NoEncontrado("Trabajador no encontrado")
        trabajador.nombre = cmd.nombre.strip()
        trabajador.rol = cmd.rol
        trabajador.periodicidad_pago = cmd.periodicidad_pago
        trabajador.definir_remuneracion(
            cmd.tipo_remuneracion,
            monto_periodo=cmd.monto_periodo,
            valor_hora=cmd.valor_hora,
            porcentaje_comision=cmd.porcentaje_comision,
        )
        self._repo.guardar(trabajador)
        return trabajador


class ArchivarTrabajador:
    """Archivar también quita el acceso al sistema."""

    def __init__(
        self, repo: TrabajadorRepository, clock: Clock, usuarios: UsuarioRepository | None = None
    ) -> None:
        self._repo = repo
        self._clock = clock
        self._usuarios = usuarios

    def execute(self, trabajador_id: UUID) -> Trabajador:
        trabajador = self._repo.obtener(trabajador_id)
        if trabajador is None:
            raise NoEncontrado("Trabajador no encontrado")
        if self._usuarios is not None:
            revocar_acceso(self._usuarios, trabajador.id)
        trabajador.archivar(self._clock.ahora())
        self._repo.guardar(trabajador)
        return trabajador


@dataclass(frozen=True, slots=True)
class ListarTrabajadoresQuery:
    q: str | None = None
    incluir_archivados: bool = False


class ListarTrabajadores:
    def __init__(self, repo: TrabajadorRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarTrabajadoresQuery) -> list[Trabajador]:
        return self._repo.listar(q=query.q, incluir_archivados=query.incluir_archivados)

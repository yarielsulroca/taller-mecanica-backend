from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from taller.domain.entities.proveedor import Proveedor
from taller.domain.enums import CondicionIva, FormaJuridica, TipoPersona
from taller.domain.exceptions import Duplicado, NoEncontrado
from taller.domain.ports import Clock
from taller.domain.ports.repositories import ProveedorRepository
from taller.domain.value_objects.cuit import Cuit
from taller.domain.value_objects.razon_social import inferir_forma_juridica


@dataclass(frozen=True, slots=True)
class CrearProveedorCommand:
    razon_social: str
    cuit: str
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: str | None = None
    cond_pago: str | None = None
    cond_iva: CondicionIva | None = None


class CrearProveedor:
    def __init__(self, repo: ProveedorRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CrearProveedorCommand) -> Proveedor:
        cuit = Cuit(cmd.cuit)
        if self._repo.existe_cuit(str(cuit)):
            raise Duplicado("Ya existe un proveedor con ese CUIT", details={"cuit": str(cuit)})
        proveedor = Proveedor(
            razon_social=cmd.razon_social.strip(),
            cuit=cuit,
            tipo_persona=cmd.tipo_persona,
            forma_juridica=cmd.forma_juridica or inferir_forma_juridica(cmd.razon_social),
            telefono=cmd.telefono,
            email=cmd.email,
            cond_pago=cmd.cond_pago,
            cond_iva=cmd.cond_iva,
        )
        self._repo.guardar(proveedor)
        return proveedor


@dataclass(frozen=True, slots=True)
class ActualizarProveedorCommand:
    proveedor_id: UUID
    razon_social: str
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: str | None = None
    cond_pago: str | None = None
    cond_iva: CondicionIva | None = None


class ActualizarProveedor:
    def __init__(self, repo: ProveedorRepository) -> None:
        self._repo = repo

    def execute(self, cmd: ActualizarProveedorCommand) -> Proveedor:
        proveedor = self._repo.obtener(cmd.proveedor_id)
        if proveedor is None:
            raise NoEncontrado("Proveedor no encontrado")
        proveedor.razon_social = cmd.razon_social.strip()
        proveedor.tipo_persona = cmd.tipo_persona
        proveedor.forma_juridica = cmd.forma_juridica or inferir_forma_juridica(cmd.razon_social)
        proveedor.telefono = cmd.telefono
        proveedor.email = cmd.email
        proveedor.cond_pago = cmd.cond_pago
        proveedor.cond_iva = cmd.cond_iva
        self._repo.guardar(proveedor)
        return proveedor


class ArchivarProveedor:
    def __init__(self, repo: ProveedorRepository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def execute(self, proveedor_id: UUID) -> Proveedor:
        proveedor = self._repo.obtener(proveedor_id)
        if proveedor is None:
            raise NoEncontrado("Proveedor no encontrado")
        proveedor.archivar(self._clock.ahora())
        self._repo.guardar(proveedor)
        return proveedor


@dataclass(frozen=True, slots=True)
class ListarProveedoresQuery:
    q: str | None = None
    incluir_archivados: bool = False


class ListarProveedores:
    def __init__(self, repo: ProveedorRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarProveedoresQuery) -> list[Proveedor]:
        return self._repo.listar(q=query.q, incluir_archivados=query.incluir_archivados)

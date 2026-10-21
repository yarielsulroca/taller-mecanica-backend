from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from taller.domain.entities.empresa import Empresa
from taller.domain.enums import CondicionIva, FormaJuridica, TipoPersona
from taller.domain.exceptions import Duplicado, NoEncontrado
from taller.domain.ports import Clock
from taller.domain.ports.repositories import EmpresaRepository
from taller.domain.value_objects.cuit import Cuit
from taller.domain.value_objects.razon_social import inferir_forma_juridica


@dataclass(frozen=True, slots=True)
class CrearEmpresaCommand:
    razon_social: str
    cuit: str
    cond_iva: CondicionIva
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None


class CrearEmpresa:
    def __init__(self, repo: EmpresaRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CrearEmpresaCommand) -> Empresa:
        cuit = Cuit(cmd.cuit)
        if self._repo.existe_cuit(str(cuit)):
            raise Duplicado("Ya existe una empresa con ese CUIT", details={"cuit": str(cuit)})
        empresa = Empresa(
            razon_social=cmd.razon_social.strip(),
            cuit=cuit,
            cond_iva=cmd.cond_iva,
            tipo_persona=cmd.tipo_persona,
            forma_juridica=cmd.forma_juridica or inferir_forma_juridica(cmd.razon_social),
            telefono=cmd.telefono,
            email=cmd.email,
            direccion=cmd.direccion,
        )
        self._repo.guardar(empresa)
        return empresa


@dataclass(frozen=True, slots=True)
class ActualizarEmpresaCommand:
    empresa_id: UUID
    razon_social: str
    cond_iva: CondicionIva
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None


class ActualizarEmpresa:
    def __init__(self, repo: EmpresaRepository) -> None:
        self._repo = repo

    def execute(self, cmd: ActualizarEmpresaCommand) -> Empresa:
        empresa = self._repo.obtener(cmd.empresa_id)
        if empresa is None:
            raise NoEncontrado("Empresa no encontrada")
        empresa.razon_social = cmd.razon_social.strip()
        empresa.cond_iva = cmd.cond_iva
        empresa.tipo_persona = cmd.tipo_persona
        empresa.forma_juridica = cmd.forma_juridica or inferir_forma_juridica(cmd.razon_social)
        empresa.telefono = cmd.telefono
        empresa.email = cmd.email
        empresa.direccion = cmd.direccion
        self._repo.guardar(empresa)
        return empresa


class ArchivarEmpresa:
    def __init__(self, repo: EmpresaRepository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def execute(self, empresa_id: UUID) -> Empresa:
        empresa = self._repo.obtener(empresa_id)
        if empresa is None:
            raise NoEncontrado("Empresa no encontrada")
        empresa.archivar(self._clock.ahora())
        self._repo.guardar(empresa)
        return empresa


@dataclass(frozen=True, slots=True)
class ListarEmpresasQuery:
    q: str | None = None
    incluir_archivados: bool = False


class ListarEmpresas:
    def __init__(self, repo: EmpresaRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarEmpresasQuery) -> list[Empresa]:
        return self._repo.listar(q=query.q, incluir_archivados=query.incluir_archivados)

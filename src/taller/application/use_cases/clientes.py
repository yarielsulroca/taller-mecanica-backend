from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from taller.domain.entities.cliente import Cliente
from taller.domain.enums import CondicionIva, FormaJuridica, TipoDocumento, TipoPersona
from taller.domain.exceptions import NoEncontrado, SolicitudInvalida
from taller.domain.ports import Clock
from taller.domain.ports.repositories import ClienteRepository, EmpresaRepository
from taller.domain.value_objects.razon_social import inferir_forma_juridica


def _validar(cmd_nombre: str, tipo_doc: TipoDocumento, nro_doc: str) -> None:
    if not cmd_nombre.strip():
        raise SolicitudInvalida("El nombre del cliente es obligatorio")
    if not nro_doc.strip():
        raise SolicitudInvalida("El número de documento es obligatorio")


@dataclass(frozen=True, slots=True)
class CrearClienteCommand:
    nombre: str
    tipo_doc: TipoDocumento
    nro_doc: str
    cond_iva: CondicionIva = CondicionIva.CONSUMIDOR_FINAL
    tipo_persona: TipoPersona = TipoPersona.FISICA
    forma_juridica: FormaJuridica | None = None
    empresa_id: UUID | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None


class CrearCliente:
    def __init__(self, repo: ClienteRepository, empresas: EmpresaRepository) -> None:
        self._repo = repo
        self._empresas = empresas

    def execute(self, cmd: CrearClienteCommand) -> Cliente:
        _validar(cmd.nombre, cmd.tipo_doc, cmd.nro_doc)
        if cmd.empresa_id is not None and self._empresas.obtener(cmd.empresa_id) is None:
            raise NoEncontrado("La empresa indicada no existe")
        cliente = Cliente(
            nombre=cmd.nombre.strip(),
            tipo_doc=cmd.tipo_doc,
            nro_doc=cmd.nro_doc.strip(),
            cond_iva=cmd.cond_iva,
            tipo_persona=cmd.tipo_persona,
            forma_juridica=cmd.forma_juridica or inferir_forma_juridica(cmd.nombre),
            empresa_id=cmd.empresa_id,
            telefono=cmd.telefono,
            email=cmd.email,
            direccion=cmd.direccion,
        )
        self._repo.guardar(cliente)
        return cliente


@dataclass(frozen=True, slots=True)
class ActualizarClienteCommand:
    cliente_id: UUID
    nombre: str
    tipo_doc: TipoDocumento
    nro_doc: str
    cond_iva: CondicionIva
    tipo_persona: TipoPersona = TipoPersona.FISICA
    forma_juridica: FormaJuridica | None = None
    empresa_id: UUID | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None


class ActualizarCliente:
    def __init__(self, repo: ClienteRepository, empresas: EmpresaRepository) -> None:
        self._repo = repo
        self._empresas = empresas

    def execute(self, cmd: ActualizarClienteCommand) -> Cliente:
        _validar(cmd.nombre, cmd.tipo_doc, cmd.nro_doc)
        cliente = self._repo.obtener(cmd.cliente_id)
        if cliente is None:
            raise NoEncontrado("Cliente no encontrado")
        if cmd.empresa_id is not None and self._empresas.obtener(cmd.empresa_id) is None:
            raise NoEncontrado("La empresa indicada no existe")
        cliente.nombre = cmd.nombre.strip()
        cliente.tipo_doc = cmd.tipo_doc
        cliente.nro_doc = cmd.nro_doc.strip()
        cliente.cond_iva = cmd.cond_iva
        cliente.tipo_persona = cmd.tipo_persona
        cliente.forma_juridica = cmd.forma_juridica or inferir_forma_juridica(cmd.nombre)
        cliente.empresa_id = cmd.empresa_id
        cliente.telefono = cmd.telefono
        cliente.email = cmd.email
        cliente.direccion = cmd.direccion
        self._repo.guardar(cliente)
        return cliente


class ArchivarCliente:
    def __init__(self, repo: ClienteRepository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def execute(self, cliente_id: UUID) -> Cliente:
        cliente = self._repo.obtener(cliente_id)
        if cliente is None:
            raise NoEncontrado("Cliente no encontrado")
        cliente.archivar(self._clock.ahora())
        self._repo.guardar(cliente)
        return cliente


@dataclass(frozen=True, slots=True)
class ListarClientesQuery:
    q: str | None = None
    empresa_id: UUID | None = None
    incluir_archivados: bool = False


class ListarClientes:
    def __init__(self, repo: ClienteRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarClientesQuery) -> list[Cliente]:
        return self._repo.listar(
            q=query.q,
            empresa_id=query.empresa_id,
            incluir_archivados=query.incluir_archivados,
        )

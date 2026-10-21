from __future__ import annotations

from dataclasses import dataclass, field

from taller.domain.entities.catalogos import Rubro, TipoPago
from taller.domain.ports.repositories import RubroRepository, TipoPagoRepository


@dataclass(frozen=True, slots=True)
class CrearRubroCommand:
    nombre: str
    tipo: str | None = None


class CrearRubro:
    def __init__(self, repo: RubroRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CrearRubroCommand) -> Rubro:
        rubro = Rubro(nombre=cmd.nombre.strip(), tipo=cmd.tipo)
        self._repo.guardar(rubro)
        return rubro


@dataclass(frozen=True, slots=True)
class ListarRubrosQuery:
    incluir_archivados: bool = False


class ListarRubros:
    def __init__(self, repo: RubroRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarRubrosQuery) -> list[Rubro]:
        return self._repo.listar(incluir_archivados=query.incluir_archivados)


@dataclass(frozen=True, slots=True)
class CrearTipoPagoCommand:
    nombre: str
    schema_extra: dict[str, object] = field(default_factory=dict)


class CrearTipoPago:
    def __init__(self, repo: TipoPagoRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CrearTipoPagoCommand) -> TipoPago:
        tipo_pago = TipoPago(nombre=cmd.nombre.strip(), schema_extra=cmd.schema_extra)
        self._repo.guardar(tipo_pago)
        return tipo_pago


@dataclass(frozen=True, slots=True)
class ListarTiposPagoQuery:
    incluir_archivados: bool = False


class ListarTiposPago:
    def __init__(self, repo: TipoPagoRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarTiposPagoQuery) -> list[TipoPago]:
        return self._repo.listar(incluir_archivados=query.incluir_archivados)


@dataclass(frozen=True, slots=True)
class SembrarCatalogosCommand:
    rubros: tuple[tuple[str, str], ...]  # (nombre, tipo)
    tipos_pago: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResultadoSiembra:
    rubros_creados: tuple[str, ...]
    tipos_pago_creados: tuple[str, ...]


class SembrarCatalogos:
    """Carga inicial idempotente: sólo agrega los nombres que no existen.

    Compara sin mayúsculas e incluye los archivados, así lo que el admin
    archivó a propósito no reaparece.
    """

    def __init__(self, rubros: RubroRepository, tipos_pago: TipoPagoRepository) -> None:
        self._rubros = rubros
        self._tipos = tipos_pago

    def execute(self, cmd: SembrarCatalogosCommand) -> ResultadoSiembra:
        existentes = {r.nombre.casefold() for r in self._rubros.listar(incluir_archivados=True)}
        rubros: list[str] = []
        for nombre, tipo in cmd.rubros:
            if nombre.casefold() not in existentes:
                self._rubros.guardar(Rubro(nombre=nombre, tipo=tipo))
                existentes.add(nombre.casefold())
                rubros.append(nombre)

        existentes = {t.nombre.casefold() for t in self._tipos.listar(incluir_archivados=True)}
        tipos: list[str] = []
        for nombre in cmd.tipos_pago:
            if nombre.casefold() not in existentes:
                self._tipos.guardar(TipoPago(nombre=nombre))
                existentes.add(nombre.casefold())
                tipos.append(nombre)
        return ResultadoSiembra(rubros_creados=tuple(rubros), tipos_pago_creados=tuple(tipos))

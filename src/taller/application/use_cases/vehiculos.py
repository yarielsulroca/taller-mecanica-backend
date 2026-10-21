from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from taller.domain.entities.vehiculo import Vehiculo
from taller.domain.exceptions import Duplicado, KmInvalido, NoEncontrado
from taller.domain.ports import Clock
from taller.domain.ports.repositories import ClienteRepository, VehiculoRepository
from taller.domain.value_objects.patente import Patente


@dataclass(frozen=True, slots=True)
class CrearVehiculoCommand:
    patente: str
    cliente_id: UUID
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = None
    vin: str | None = None
    motor: str | None = None
    color: str | None = None
    km_actual: int = 0


class CrearVehiculo:
    def __init__(self, repo: VehiculoRepository, clientes: ClienteRepository) -> None:
        self._repo = repo
        self._clientes = clientes

    def execute(self, cmd: CrearVehiculoCommand) -> Vehiculo:
        patente = Patente(cmd.patente)
        if self._clientes.obtener(cmd.cliente_id) is None:
            raise NoEncontrado("El cliente indicado no existe")
        if self._repo.existe_patente(str(patente)):
            raise Duplicado(
                "Ya existe un vehículo con esa patente",
                details={"patente": str(patente)},
            )
        vehiculo = Vehiculo(
            patente=patente,
            cliente_id=cmd.cliente_id,
            marca=cmd.marca,
            modelo=cmd.modelo,
            anio=cmd.anio,
            vin=cmd.vin,
            motor=cmd.motor,
            color=cmd.color,
            km_actual=cmd.km_actual,
        )
        self._repo.guardar(vehiculo)
        return vehiculo


@dataclass(frozen=True, slots=True)
class ActualizarVehiculoCommand:
    vehiculo_id: UUID
    patente: str
    cliente_id: UUID
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = None
    vin: str | None = None
    motor: str | None = None
    color: str | None = None
    km_actual: int | None = None


class ActualizarVehiculo:
    def __init__(self, repo: VehiculoRepository, clientes: ClienteRepository) -> None:
        self._repo = repo
        self._clientes = clientes

    def execute(self, cmd: ActualizarVehiculoCommand) -> Vehiculo:
        vehiculo = self._repo.obtener(cmd.vehiculo_id)
        if vehiculo is None:
            raise NoEncontrado("Vehículo no encontrado")
        patente = Patente(cmd.patente)
        if self._repo.existe_patente(str(patente), excluir_id=vehiculo.id):
            raise Duplicado(
                "Ya existe otro vehículo con esa patente",
                details={"patente": str(patente)},
            )
        if self._clientes.obtener(cmd.cliente_id) is None:
            raise NoEncontrado("El cliente indicado no existe")
        if cmd.km_actual is not None and cmd.km_actual < vehiculo.km_actual:
            raise KmInvalido("El kilometraje no puede disminuir")
        vehiculo.patente = patente
        vehiculo.cliente_id = cmd.cliente_id
        vehiculo.marca = cmd.marca
        vehiculo.modelo = cmd.modelo
        vehiculo.anio = cmd.anio
        vehiculo.vin = cmd.vin
        vehiculo.motor = cmd.motor
        vehiculo.color = cmd.color
        if cmd.km_actual is not None:
            vehiculo.km_actual = cmd.km_actual
        self._repo.guardar(vehiculo)
        return vehiculo


class ArchivarVehiculo:
    def __init__(self, repo: VehiculoRepository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def execute(self, vehiculo_id: UUID) -> Vehiculo:
        vehiculo = self._repo.obtener(vehiculo_id)
        if vehiculo is None:
            raise NoEncontrado("Vehículo no encontrado")
        vehiculo.archivar(self._clock.ahora())
        self._repo.guardar(vehiculo)
        return vehiculo


@dataclass(frozen=True, slots=True)
class ListarVehiculosQuery:
    cliente_id: UUID | None = None
    q: str | None = None
    incluir_archivados: bool = False


class ListarVehiculos:
    def __init__(self, repo: VehiculoRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarVehiculosQuery) -> list[Vehiculo]:
        return self._repo.listar(
            cliente_id=query.cliente_id,
            q=query.q,
            incluir_archivados=query.incluir_archivados,
        )


class ObtenerVehiculo:
    def __init__(self, repo: VehiculoRepository) -> None:
        self._repo = repo

    def execute(self, vehiculo_id: UUID) -> Vehiculo:
        vehiculo = self._repo.obtener(vehiculo_id)
        if vehiculo is None:
            raise NoEncontrado("Vehículo no encontrado")
        return vehiculo


class ObtenerVehiculoPorPatente:
    def __init__(self, repo: VehiculoRepository) -> None:
        self._repo = repo

    def execute(self, patente: str) -> Vehiculo:
        vehiculo = self._repo.obtener_por_patente(str(Patente(patente)))
        if vehiculo is None:
            raise NoEncontrado("Vehículo no encontrado")
        return vehiculo

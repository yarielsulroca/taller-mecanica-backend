from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_container, get_session, get_usuario_repo
from taller.adapters.outbound.postgres.maestros_repositories import (
    SqlClienteRepository,
    SqlEmpresaRepository,
    SqlFotoVehiculoRepository,
    SqlProveedorRepository,
    SqlRubroRepository,
    SqlTipoPagoRepository,
    SqlTrabajadorRepository,
    SqlVehiculoRepository,
)
from taller.adapters.outbound.postgres.usuario_repository import SqlUsuarioRepository
from taller.application.use_cases.catalogos import (
    CrearRubro,
    CrearTipoPago,
    ListarRubros,
    ListarTiposPago,
)
from taller.application.use_cases.clientes import (
    ActualizarCliente,
    ArchivarCliente,
    CrearCliente,
    ListarClientes,
)
from taller.application.use_cases.empresas import (
    ActualizarEmpresa,
    ArchivarEmpresa,
    CrearEmpresa,
    ListarEmpresas,
)
from taller.application.use_cases.fotos_vehiculo import (
    CambiarVistaFoto,
    FotosDelanteras,
    ListarFotosVehiculo,
    ObtenerArchivoFotoVehiculo,
    QuitarFotoVehiculo,
    SubirFotosVehiculo,
)
from taller.application.use_cases.proveedores import (
    ActualizarProveedor,
    ArchivarProveedor,
    CrearProveedor,
    ListarProveedores,
)
from taller.application.use_cases.trabajadores import (
    ActualizarTrabajador,
    ArchivarTrabajador,
    CrearTrabajador,
    ListarTrabajadores,
)
from taller.application.use_cases.vehiculos import (
    ActualizarVehiculo,
    ArchivarVehiculo,
    CrearVehiculo,
    ListarVehiculos,
    ObtenerVehiculo,
    ObtenerVehiculoPorPatente,
)
from taller.container import Container


# --- Repositorios -----------------------------------------------------------
def repo_empresas(session: Annotated[Session, Depends(get_session)]) -> SqlEmpresaRepository:
    return SqlEmpresaRepository(session)


def repo_clientes(session: Annotated[Session, Depends(get_session)]) -> SqlClienteRepository:
    return SqlClienteRepository(session)


def repo_vehiculos(session: Annotated[Session, Depends(get_session)]) -> SqlVehiculoRepository:
    return SqlVehiculoRepository(session)


def repo_proveedores(session: Annotated[Session, Depends(get_session)]) -> SqlProveedorRepository:
    return SqlProveedorRepository(session)


def repo_trabajadores(session: Annotated[Session, Depends(get_session)]) -> SqlTrabajadorRepository:
    return SqlTrabajadorRepository(session)


def repo_rubros(session: Annotated[Session, Depends(get_session)]) -> SqlRubroRepository:
    return SqlRubroRepository(session)


def repo_tipos_pago(session: Annotated[Session, Depends(get_session)]) -> SqlTipoPagoRepository:
    return SqlTipoPagoRepository(session)


# --- Empresas ---------------------------------------------------------------
def uc_crear_empresa(
    repo: Annotated[SqlEmpresaRepository, Depends(repo_empresas)],
) -> CrearEmpresa:
    return CrearEmpresa(repo)


def uc_actualizar_empresa(
    repo: Annotated[SqlEmpresaRepository, Depends(repo_empresas)],
) -> ActualizarEmpresa:
    return ActualizarEmpresa(repo)


def uc_archivar_empresa(
    repo: Annotated[SqlEmpresaRepository, Depends(repo_empresas)],
    container: Annotated[Container, Depends(get_container)],
) -> ArchivarEmpresa:
    return ArchivarEmpresa(repo, container.clock)


def uc_listar_empresas(
    repo: Annotated[SqlEmpresaRepository, Depends(repo_empresas)],
) -> ListarEmpresas:
    return ListarEmpresas(repo)


# --- Clientes ---------------------------------------------------------------
def uc_crear_cliente(
    repo: Annotated[SqlClienteRepository, Depends(repo_clientes)],
    empresas: Annotated[SqlEmpresaRepository, Depends(repo_empresas)],
) -> CrearCliente:
    return CrearCliente(repo, empresas)


def uc_actualizar_cliente(
    repo: Annotated[SqlClienteRepository, Depends(repo_clientes)],
    empresas: Annotated[SqlEmpresaRepository, Depends(repo_empresas)],
) -> ActualizarCliente:
    return ActualizarCliente(repo, empresas)


def uc_archivar_cliente(
    repo: Annotated[SqlClienteRepository, Depends(repo_clientes)],
    container: Annotated[Container, Depends(get_container)],
) -> ArchivarCliente:
    return ArchivarCliente(repo, container.clock)


def uc_listar_clientes(
    repo: Annotated[SqlClienteRepository, Depends(repo_clientes)],
) -> ListarClientes:
    return ListarClientes(repo)


# --- Vehículos --------------------------------------------------------------
def uc_crear_vehiculo(
    repo: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
    clientes: Annotated[SqlClienteRepository, Depends(repo_clientes)],
) -> CrearVehiculo:
    return CrearVehiculo(repo, clientes)


def uc_actualizar_vehiculo(
    repo: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
    clientes: Annotated[SqlClienteRepository, Depends(repo_clientes)],
) -> ActualizarVehiculo:
    return ActualizarVehiculo(repo, clientes)


def uc_archivar_vehiculo(
    repo: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
    container: Annotated[Container, Depends(get_container)],
) -> ArchivarVehiculo:
    return ArchivarVehiculo(repo, container.clock)


def uc_listar_vehiculos(
    repo: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
) -> ListarVehiculos:
    return ListarVehiculos(repo)


def uc_obtener_vehiculo_por_patente(
    repo: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
) -> ObtenerVehiculoPorPatente:
    return ObtenerVehiculoPorPatente(repo)


def uc_obtener_vehiculo(
    repo: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
) -> ObtenerVehiculo:
    return ObtenerVehiculo(repo)


def repo_fotos_vehiculo(
    session: Annotated[Session, Depends(get_session)],
) -> SqlFotoVehiculoRepository:
    return SqlFotoVehiculoRepository(session)


def uc_subir_fotos_vehiculo(
    fotos: Annotated[SqlFotoVehiculoRepository, Depends(repo_fotos_vehiculo)],
    vehiculos: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
    container: Annotated[Container, Depends(get_container)],
) -> SubirFotosVehiculo:
    return SubirFotosVehiculo(fotos, vehiculos, container.storage, container.clock)


def uc_listar_fotos_vehiculo(
    fotos: Annotated[SqlFotoVehiculoRepository, Depends(repo_fotos_vehiculo)],
    vehiculos: Annotated[SqlVehiculoRepository, Depends(repo_vehiculos)],
) -> ListarFotosVehiculo:
    return ListarFotosVehiculo(fotos, vehiculos)


def uc_archivo_foto_vehiculo(
    fotos: Annotated[SqlFotoVehiculoRepository, Depends(repo_fotos_vehiculo)],
    container: Annotated[Container, Depends(get_container)],
) -> ObtenerArchivoFotoVehiculo:
    return ObtenerArchivoFotoVehiculo(fotos, container.storage)


def uc_cambiar_vista_foto(
    fotos: Annotated[SqlFotoVehiculoRepository, Depends(repo_fotos_vehiculo)],
) -> CambiarVistaFoto:
    return CambiarVistaFoto(fotos)


def uc_fotos_delanteras(
    fotos: Annotated[SqlFotoVehiculoRepository, Depends(repo_fotos_vehiculo)],
) -> FotosDelanteras:
    return FotosDelanteras(fotos)


def uc_quitar_foto_vehiculo(
    fotos: Annotated[SqlFotoVehiculoRepository, Depends(repo_fotos_vehiculo)],
    container: Annotated[Container, Depends(get_container)],
) -> QuitarFotoVehiculo:
    return QuitarFotoVehiculo(fotos, container.clock)


# --- Proveedores ------------------------------------------------------------
def uc_crear_proveedor(
    repo: Annotated[SqlProveedorRepository, Depends(repo_proveedores)],
) -> CrearProveedor:
    return CrearProveedor(repo)


def uc_actualizar_proveedor(
    repo: Annotated[SqlProveedorRepository, Depends(repo_proveedores)],
) -> ActualizarProveedor:
    return ActualizarProveedor(repo)


def uc_archivar_proveedor(
    repo: Annotated[SqlProveedorRepository, Depends(repo_proveedores)],
    container: Annotated[Container, Depends(get_container)],
) -> ArchivarProveedor:
    return ArchivarProveedor(repo, container.clock)


def uc_listar_proveedores(
    repo: Annotated[SqlProveedorRepository, Depends(repo_proveedores)],
) -> ListarProveedores:
    return ListarProveedores(repo)


# --- Trabajadores -----------------------------------------------------------
def uc_crear_trabajador(
    repo: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores)],
) -> CrearTrabajador:
    return CrearTrabajador(repo)


def uc_actualizar_trabajador(
    repo: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores)],
) -> ActualizarTrabajador:
    return ActualizarTrabajador(repo)


def uc_archivar_trabajador(
    repo: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores)],
    container: Annotated[Container, Depends(get_container)],
    usuarios: Annotated[SqlUsuarioRepository, Depends(get_usuario_repo)],
) -> ArchivarTrabajador:
    return ArchivarTrabajador(repo, container.clock, usuarios)


def uc_listar_trabajadores(
    repo: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores)],
) -> ListarTrabajadores:
    return ListarTrabajadores(repo)


# --- Catálogos --------------------------------------------------------------
def uc_crear_rubro(
    repo: Annotated[SqlRubroRepository, Depends(repo_rubros)],
) -> CrearRubro:
    return CrearRubro(repo)


def uc_listar_rubros(
    repo: Annotated[SqlRubroRepository, Depends(repo_rubros)],
) -> ListarRubros:
    return ListarRubros(repo)


def uc_crear_tipo_pago(
    repo: Annotated[SqlTipoPagoRepository, Depends(repo_tipos_pago)],
) -> CrearTipoPago:
    return CrearTipoPago(repo)


def uc_listar_tipos_pago(
    repo: Annotated[SqlTipoPagoRepository, Depends(repo_tipos_pago)],
) -> ListarTiposPago:
    return ListarTiposPago(repo)

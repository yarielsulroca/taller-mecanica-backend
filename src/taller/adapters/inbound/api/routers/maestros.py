from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from taller.adapters.inbound.api.deps import get_current_user, require_roles
from taller.adapters.inbound.api.deps_maestros import (
    uc_actualizar_cliente,
    uc_actualizar_empresa,
    uc_actualizar_proveedor,
    uc_actualizar_trabajador,
    uc_actualizar_vehiculo,
    uc_archivar_cliente,
    uc_archivar_empresa,
    uc_archivar_proveedor,
    uc_archivar_trabajador,
    uc_archivar_vehiculo,
    uc_archivo_foto_vehiculo,
    uc_cambiar_vista_foto,
    uc_crear_cliente,
    uc_crear_empresa,
    uc_crear_proveedor,
    uc_crear_rubro,
    uc_crear_tipo_pago,
    uc_crear_trabajador,
    uc_crear_vehiculo,
    uc_fotos_delanteras,
    uc_listar_clientes,
    uc_listar_empresas,
    uc_listar_fotos_vehiculo,
    uc_listar_proveedores,
    uc_listar_rubros,
    uc_listar_tipos_pago,
    uc_listar_trabajadores,
    uc_listar_vehiculos,
    uc_obtener_vehiculo,
    uc_obtener_vehiculo_por_patente,
    uc_quitar_foto_vehiculo,
    uc_subir_fotos_vehiculo,
)
from taller.adapters.inbound.api.schemas_maestros import (
    ClienteCreate,
    ClienteResponse,
    ClienteUpdate,
    EmpresaCreate,
    EmpresaResponse,
    EmpresaUpdate,
    FotoVehiculoResponse,
    FotoVistaUpdate,
    OpcionResponse,
    ProveedorCreate,
    ProveedorResponse,
    ProveedorUpdate,
    RubroCreate,
    RubroResponse,
    TipoPagoCreate,
    TipoPagoResponse,
    TrabajadorCreate,
    TrabajadorResponse,
    TrabajadorUpdate,
    VehiculoCreate,
    VehiculoResponse,
    VehiculoUpdate,
)
from taller.application.use_cases.catalogos import (
    CrearRubro,
    CrearRubroCommand,
    CrearTipoPago,
    CrearTipoPagoCommand,
    ListarRubros,
    ListarRubrosQuery,
    ListarTiposPago,
    ListarTiposPagoQuery,
)
from taller.application.use_cases.clientes import (
    ActualizarCliente,
    ActualizarClienteCommand,
    ArchivarCliente,
    CrearCliente,
    CrearClienteCommand,
    ListarClientes,
    ListarClientesQuery,
)
from taller.application.use_cases.empresas import (
    ActualizarEmpresa,
    ActualizarEmpresaCommand,
    ArchivarEmpresa,
    CrearEmpresa,
    CrearEmpresaCommand,
    ListarEmpresas,
    ListarEmpresasQuery,
)
from taller.application.use_cases.fotos_vehiculo import (
    ArchivoSubido,
    CambiarVistaFoto,
    FotosDelanteras,
    ListarFotosVehiculo,
    ObtenerArchivoFotoVehiculo,
    QuitarFotoVehiculo,
    SubirFotosVehiculo,
    SubirFotosVehiculoCommand,
)
from taller.application.use_cases.proveedores import (
    ActualizarProveedor,
    ActualizarProveedorCommand,
    ArchivarProveedor,
    CrearProveedor,
    CrearProveedorCommand,
    ListarProveedores,
    ListarProveedoresQuery,
)
from taller.application.use_cases.trabajadores import (
    ActualizarTrabajador,
    ActualizarTrabajadorCommand,
    ArchivarTrabajador,
    CrearTrabajador,
    CrearTrabajadorCommand,
    ListarTrabajadores,
    ListarTrabajadoresQuery,
)
from taller.application.use_cases.vehiculos import (
    ActualizarVehiculo,
    ActualizarVehiculoCommand,
    ArchivarVehiculo,
    CrearVehiculo,
    CrearVehiculoCommand,
    ListarVehiculos,
    ListarVehiculosQuery,
    ObtenerVehiculo,
    ObtenerVehiculoPorPatente,
)
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.enums import ETIQUETAS_CONDICION_IVA, CondicionIva, VistaFoto
from taller.domain.exceptions import NoEncontrado

# Escritura de maestros: admin, administración y recepción (matriz RBAC).
puede_gestionar = require_roles(Rol.ADMIN, Rol.ADMINISTRACION, Rol.RECEPCION)
Gestor = Annotated[Usuario, Depends(puede_gestionar)]
Lector = Annotated[Usuario, Depends(get_current_user)]

router = APIRouter(tags=["maestros"])


# --- Empresas ---------------------------------------------------------------
@router.get("/empresas", response_model=list[EmpresaResponse])
def listar_empresas(
    _: Lector,
    uc: Annotated[ListarEmpresas, Depends(uc_listar_empresas)],
    q: Annotated[str | None, Query()] = None,
    incluir_archivados: Annotated[bool, Query()] = False,
) -> list[EmpresaResponse]:
    empresas = uc.execute(ListarEmpresasQuery(q=q, incluir_archivados=incluir_archivados))
    return [EmpresaResponse.desde(e) for e in empresas]


@router.post("/empresas", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
def crear_empresa(
    _: Gestor,
    payload: EmpresaCreate,
    uc: Annotated[CrearEmpresa, Depends(uc_crear_empresa)],
) -> EmpresaResponse:
    return EmpresaResponse.desde(uc.execute(CrearEmpresaCommand(**payload.model_dump())))


@router.patch("/empresas/{empresa_id}", response_model=EmpresaResponse)
def actualizar_empresa(
    empresa_id: UUID,
    _: Gestor,
    payload: EmpresaUpdate,
    uc: Annotated[ActualizarEmpresa, Depends(uc_actualizar_empresa)],
) -> EmpresaResponse:
    cmd = ActualizarEmpresaCommand(empresa_id=empresa_id, **payload.model_dump())
    return EmpresaResponse.desde(uc.execute(cmd))


@router.post("/empresas/{empresa_id}/archivar", response_model=EmpresaResponse)
def archivar_empresa(
    empresa_id: UUID,
    _: Gestor,
    uc: Annotated[ArchivarEmpresa, Depends(uc_archivar_empresa)],
) -> EmpresaResponse:
    return EmpresaResponse.desde(uc.execute(empresa_id))


# --- Clientes ---------------------------------------------------------------
@router.get("/clientes", response_model=list[ClienteResponse])
def listar_clientes(
    _: Lector,
    uc: Annotated[ListarClientes, Depends(uc_listar_clientes)],
    q: Annotated[str | None, Query()] = None,
    empresa_id: Annotated[UUID | None, Query()] = None,
    incluir_archivados: Annotated[bool, Query()] = False,
) -> list[ClienteResponse]:
    query = ListarClientesQuery(q=q, empresa_id=empresa_id, incluir_archivados=incluir_archivados)
    return [ClienteResponse.desde(c) for c in uc.execute(query)]


@router.post("/clientes", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    _: Gestor,
    payload: ClienteCreate,
    uc: Annotated[CrearCliente, Depends(uc_crear_cliente)],
) -> ClienteResponse:
    return ClienteResponse.desde(uc.execute(CrearClienteCommand(**payload.model_dump())))


@router.patch("/clientes/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: UUID,
    _: Gestor,
    payload: ClienteUpdate,
    uc: Annotated[ActualizarCliente, Depends(uc_actualizar_cliente)],
) -> ClienteResponse:
    cmd = ActualizarClienteCommand(cliente_id=cliente_id, **payload.model_dump())
    return ClienteResponse.desde(uc.execute(cmd))


@router.post("/clientes/{cliente_id}/archivar", response_model=ClienteResponse)
def archivar_cliente(
    cliente_id: UUID,
    _: Gestor,
    uc: Annotated[ArchivarCliente, Depends(uc_archivar_cliente)],
) -> ClienteResponse:
    return ClienteResponse.desde(uc.execute(cliente_id))


# --- Vehículos --------------------------------------------------------------
@router.get("/vehiculos", response_model=list[VehiculoResponse])
def listar_vehiculos(
    _: Lector,
    uc: Annotated[ListarVehiculos, Depends(uc_listar_vehiculos)],
    delanteras: Annotated[FotosDelanteras, Depends(uc_fotos_delanteras)],
    cliente_id: Annotated[UUID | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    incluir_archivados: Annotated[bool, Query()] = False,
) -> list[VehiculoResponse]:
    query = ListarVehiculosQuery(cliente_id=cliente_id, q=q, incluir_archivados=incluir_archivados)
    vehiculos = uc.execute(query)
    portadas = delanteras.execute([v.id for v in vehiculos])
    return [VehiculoResponse.desde(v, portadas.get(v.id)) for v in vehiculos]


@router.get("/vehiculos/buscar", response_model=VehiculoResponse)
def buscar_vehiculo_por_patente(
    _: Lector,
    uc: Annotated[ObtenerVehiculoPorPatente, Depends(uc_obtener_vehiculo_por_patente)],
    patente: Annotated[str, Query(min_length=5)],
) -> VehiculoResponse:
    return VehiculoResponse.desde(uc.execute(patente))


@router.get("/vehiculos/{vehiculo_id}", response_model=VehiculoResponse)
def obtener_vehiculo(
    vehiculo_id: UUID,
    _: Lector,
    uc: Annotated[ObtenerVehiculo, Depends(uc_obtener_vehiculo)],
    delanteras: Annotated[FotosDelanteras, Depends(uc_fotos_delanteras)],
) -> VehiculoResponse:
    vehiculo = uc.execute(vehiculo_id)
    return VehiculoResponse.desde(vehiculo, delanteras.execute([vehiculo.id]).get(vehiculo.id))


@router.post("/vehiculos", response_model=VehiculoResponse, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(
    _: Gestor,
    payload: VehiculoCreate,
    uc: Annotated[CrearVehiculo, Depends(uc_crear_vehiculo)],
) -> VehiculoResponse:
    return VehiculoResponse.desde(uc.execute(CrearVehiculoCommand(**payload.model_dump())))


@router.patch("/vehiculos/{vehiculo_id}", response_model=VehiculoResponse)
def actualizar_vehiculo(
    vehiculo_id: UUID,
    _: Gestor,
    payload: VehiculoUpdate,
    uc: Annotated[ActualizarVehiculo, Depends(uc_actualizar_vehiculo)],
) -> VehiculoResponse:
    cmd = ActualizarVehiculoCommand(vehiculo_id=vehiculo_id, **payload.model_dump())
    return VehiculoResponse.desde(uc.execute(cmd))


@router.post("/vehiculos/{vehiculo_id}/archivar", response_model=VehiculoResponse)
def archivar_vehiculo(
    vehiculo_id: UUID,
    _: Gestor,
    uc: Annotated[ArchivarVehiculo, Depends(uc_archivar_vehiculo)],
) -> VehiculoResponse:
    return VehiculoResponse.desde(uc.execute(vehiculo_id))


@router.get("/vehiculos/{vehiculo_id}/fotos", response_model=list[FotoVehiculoResponse])
def listar_fotos_vehiculo(
    vehiculo_id: UUID,
    _: Lector,
    uc: Annotated[ListarFotosVehiculo, Depends(uc_listar_fotos_vehiculo)],
) -> list[FotoVehiculoResponse]:
    return [FotoVehiculoResponse.desde(f) for f in uc.execute(vehiculo_id)]


@router.post(
    "/vehiculos/{vehiculo_id}/fotos",
    response_model=list[FotoVehiculoResponse],
    status_code=status.HTTP_201_CREATED,
)
async def subir_fotos_vehiculo(
    vehiculo_id: UUID,
    usuario: Lector,
    uc: Annotated[SubirFotosVehiculo, Depends(uc_subir_fotos_vehiculo)],
    archivos: Annotated[list[UploadFile], File()],
    nota: Annotated[str | None, Form()] = None,
    vista: Annotated[VistaFoto, Form()] = VistaFoto.OTRA,
) -> list[FotoVehiculoResponse]:
    subidos = tuple(
        [
            ArchivoSubido(
                nombre_original=a.filename or "foto",
                contenido=await a.read(),
                content_type=a.content_type or "",
            )
            for a in archivos
        ]
    )
    cmd = SubirFotosVehiculoCommand(
        vehiculo_id=vehiculo_id, autor_id=usuario.id, archivos=subidos, nota=nota, vista=vista
    )
    return [FotoVehiculoResponse.desde(f) for f in uc.execute(cmd)]


@router.patch("/vehiculos/{vehiculo_id}/fotos/{foto_id}", response_model=list[FotoVehiculoResponse])
def cambiar_vista_foto(
    vehiculo_id: UUID,
    foto_id: UUID,
    _: Lector,
    payload: FotoVistaUpdate,
    uc: Annotated[CambiarVistaFoto, Depends(uc_cambiar_vista_foto)],
) -> list[FotoVehiculoResponse]:
    fotos = uc.execute(vehiculo_id, foto_id, payload.vista)
    return [FotoVehiculoResponse.desde(f) for f in fotos]


@router.get("/vehiculos/{vehiculo_id}/fotos/{foto_id}/archivo")
def archivo_foto_vehiculo(
    vehiculo_id: UUID,
    foto_id: UUID,
    _: Lector,
    uc: Annotated[ObtenerArchivoFotoVehiculo, Depends(uc_archivo_foto_vehiculo)],
) -> FileResponse:
    archivo = uc.execute(vehiculo_id, foto_id)
    if not archivo.ruta.is_file():
        raise NoEncontrado("El archivo de la foto no está disponible")
    return FileResponse(
        archivo.ruta,
        media_type=archivo.content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.delete(
    "/vehiculos/{vehiculo_id}/fotos/{foto_id}", response_model=list[FotoVehiculoResponse]
)
def quitar_foto_vehiculo(
    vehiculo_id: UUID,
    foto_id: UUID,
    _: Gestor,
    uc: Annotated[QuitarFotoVehiculo, Depends(uc_quitar_foto_vehiculo)],
) -> list[FotoVehiculoResponse]:
    return [FotoVehiculoResponse.desde(f) for f in uc.execute(vehiculo_id, foto_id)]


# --- Proveedores ------------------------------------------------------------
@router.get("/proveedores", response_model=list[ProveedorResponse])
def listar_proveedores(
    _: Lector,
    uc: Annotated[ListarProveedores, Depends(uc_listar_proveedores)],
    q: Annotated[str | None, Query()] = None,
    incluir_archivados: Annotated[bool, Query()] = False,
) -> list[ProveedorResponse]:
    proveedores = uc.execute(ListarProveedoresQuery(q=q, incluir_archivados=incluir_archivados))
    return [ProveedorResponse.desde(p) for p in proveedores]


@router.post("/proveedores", response_model=ProveedorResponse, status_code=status.HTTP_201_CREATED)
def crear_proveedor(
    _: Gestor,
    payload: ProveedorCreate,
    uc: Annotated[CrearProveedor, Depends(uc_crear_proveedor)],
) -> ProveedorResponse:
    return ProveedorResponse.desde(uc.execute(CrearProveedorCommand(**payload.model_dump())))


@router.patch("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
def actualizar_proveedor(
    proveedor_id: UUID,
    _: Gestor,
    payload: ProveedorUpdate,
    uc: Annotated[ActualizarProveedor, Depends(uc_actualizar_proveedor)],
) -> ProveedorResponse:
    cmd = ActualizarProveedorCommand(proveedor_id=proveedor_id, **payload.model_dump())
    return ProveedorResponse.desde(uc.execute(cmd))


@router.post("/proveedores/{proveedor_id}/archivar", response_model=ProveedorResponse)
def archivar_proveedor(
    proveedor_id: UUID,
    _: Gestor,
    uc: Annotated[ArchivarProveedor, Depends(uc_archivar_proveedor)],
) -> ProveedorResponse:
    return ProveedorResponse.desde(uc.execute(proveedor_id))


# --- Trabajadores -----------------------------------------------------------
@router.get("/trabajadores", response_model=list[TrabajadorResponse])
def listar_trabajadores(
    _: Lector,
    uc: Annotated[ListarTrabajadores, Depends(uc_listar_trabajadores)],
    q: Annotated[str | None, Query()] = None,
    incluir_archivados: Annotated[bool, Query()] = False,
) -> list[TrabajadorResponse]:
    trabajadores = uc.execute(ListarTrabajadoresQuery(q=q, incluir_archivados=incluir_archivados))
    return [TrabajadorResponse.desde(t) for t in trabajadores]


@router.post(
    "/trabajadores", response_model=TrabajadorResponse, status_code=status.HTTP_201_CREATED
)
def crear_trabajador(
    _: Gestor,
    payload: TrabajadorCreate,
    uc: Annotated[CrearTrabajador, Depends(uc_crear_trabajador)],
) -> TrabajadorResponse:
    return TrabajadorResponse.desde(uc.execute(CrearTrabajadorCommand(**payload.model_dump())))


@router.patch("/trabajadores/{trabajador_id}", response_model=TrabajadorResponse)
def actualizar_trabajador(
    trabajador_id: UUID,
    _: Gestor,
    payload: TrabajadorUpdate,
    uc: Annotated[ActualizarTrabajador, Depends(uc_actualizar_trabajador)],
) -> TrabajadorResponse:
    cmd = ActualizarTrabajadorCommand(trabajador_id=trabajador_id, **payload.model_dump())
    return TrabajadorResponse.desde(uc.execute(cmd))


@router.post("/trabajadores/{trabajador_id}/archivar", response_model=TrabajadorResponse)
def archivar_trabajador(
    trabajador_id: UUID,
    _: Gestor,
    uc: Annotated[ArchivarTrabajador, Depends(uc_archivar_trabajador)],
) -> TrabajadorResponse:
    return TrabajadorResponse.desde(uc.execute(trabajador_id))


# --- Catálogos --------------------------------------------------------------
@router.get("/condiciones-iva", response_model=list[OpcionResponse])
def listar_condiciones_iva(_: Lector) -> list[OpcionResponse]:
    return [
        OpcionResponse(valor=c.value, etiqueta=ETIQUETAS_CONDICION_IVA[c]) for c in CondicionIva
    ]


@router.get("/rubros", response_model=list[RubroResponse])
def listar_rubros(
    _: Lector,
    uc: Annotated[ListarRubros, Depends(uc_listar_rubros)],
    incluir_archivados: Annotated[bool, Query()] = False,
) -> list[RubroResponse]:
    rubros = uc.execute(ListarRubrosQuery(incluir_archivados=incluir_archivados))
    return [RubroResponse.desde(r) for r in rubros]


@router.post("/rubros", response_model=RubroResponse, status_code=status.HTTP_201_CREATED)
def crear_rubro(
    _: Gestor,
    payload: RubroCreate,
    uc: Annotated[CrearRubro, Depends(uc_crear_rubro)],
) -> RubroResponse:
    return RubroResponse.desde(uc.execute(CrearRubroCommand(**payload.model_dump())))


@router.get("/tipos-pago", response_model=list[TipoPagoResponse])
def listar_tipos_pago(
    _: Lector,
    uc: Annotated[ListarTiposPago, Depends(uc_listar_tipos_pago)],
    incluir_archivados: Annotated[bool, Query()] = False,
) -> list[TipoPagoResponse]:
    tipos = uc.execute(ListarTiposPagoQuery(incluir_archivados=incluir_archivados))
    return [TipoPagoResponse.desde(t) for t in tipos]


@router.post("/tipos-pago", response_model=TipoPagoResponse, status_code=status.HTTP_201_CREATED)
def crear_tipo_pago(
    _: Gestor,
    payload: TipoPagoCreate,
    uc: Annotated[CrearTipoPago, Depends(uc_crear_tipo_pago)],
) -> TipoPagoResponse:
    return TipoPagoResponse.desde(uc.execute(CrearTipoPagoCommand(**payload.model_dump())))

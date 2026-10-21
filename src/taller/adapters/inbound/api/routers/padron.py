from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from taller.adapters.inbound.api.deps import get_current_user, require_roles
from taller.adapters.inbound.api.deps_auditoria import uc_registrar_auditoria
from taller.adapters.inbound.api.deps_padron import (
    uc_cargar_credenciales_arca,
    uc_guardar_conexion_arca,
    uc_obtener_conexion_arca,
    uc_probar_conexion_arca,
    uc_resolver_padron,
    uc_sugerir_padron,
)
from taller.adapters.inbound.api.schemas_padron import (
    ConexionArcaResponse,
    ConexionArcaUpdate,
    EstadoPadronResponse,
    PruebaArcaResponse,
    SugerenciaPadronResponse,
)
from taller.adapters.outbound.clock import SystemClock
from taller.application.use_cases.auditoria import RegistrarAuditoria
from taller.application.use_cases.conexion_arca import (
    CargarCredencialesArca,
    CargarCredencialesCommand,
    GuardarConexionArca,
    GuardarConexionArcaCommand,
    ObtenerConexionArca,
    ProbarConexionArca,
    ResolverPadron,
)
from taller.application.use_cases.padron import SugerirCommand, SugerirPorCuit
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.exceptions import ServicioExternoNoDisponible

Lector = Annotated[Usuario, Depends(get_current_user)]
SoloAdmin = Annotated[Usuario, Depends(require_roles(Rol.ADMIN))]
Auditoria = Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)]

router = APIRouter(prefix="/padron", tags=["padron"])
router_arca = APIRouter(prefix="/configuracion-taller/arca", tags=["configuracion"])


def _hoy() -> date:
    return SystemClock().ahora().date()


@router.get("/estado", response_model=EstadoPadronResponse)
def estado_padron(
    _: Lector,
    uc: Annotated[ResolverPadron, Depends(uc_resolver_padron)],
) -> EstadoPadronResponse:
    return EstadoPadronResponse(disponible=uc.execute() is not None)


@router.get("/{cuit}", response_model=SugerenciaPadronResponse | None)
def sugerir_por_cuit(
    cuit: str,
    _: Lector,  # cualquier usuario autenticado (altas)
    uc: Annotated[SugerirPorCuit, Depends(uc_sugerir_padron)],
) -> SugerenciaPadronResponse | None:
    """Sugerencia de datos por CUIT (razón social y condición IVA). Nunca se guarda sola."""
    datos = uc.execute(SugerirCommand(cuit=cuit))
    if datos is None:
        return None
    return SugerenciaPadronResponse.desde(datos, _hoy())


@router_arca.get("", response_model=ConexionArcaResponse)
def obtener_conexion(
    _: SoloAdmin,
    uc: Annotated[ObtenerConexionArca, Depends(uc_obtener_conexion_arca)],
) -> ConexionArcaResponse:
    return ConexionArcaResponse.desde(uc.execute(), _hoy())


@router_arca.put("", response_model=ConexionArcaResponse)
def guardar_conexion(
    usuario: SoloAdmin,
    payload: ConexionArcaUpdate,
    uc: Annotated[GuardarConexionArca, Depends(uc_guardar_conexion_arca)],
    audit: Auditoria,
) -> ConexionArcaResponse:
    conexion = uc.execute(
        GuardarConexionArcaCommand(
            activa=payload.activa,
            ambiente=payload.ambiente,
            cuit=payload.cuit,
            usuario_id=usuario.id,
        )
    )
    audit.execute(
        usuario,
        accion="activar" if conexion.activa else "desactivar",
        entidad="conexion_arca",
        entidad_id=conexion.id,
        detalle=f"ambiente={conexion.ambiente.value}",
        datos_despues={"activa": conexion.activa, "ambiente": conexion.ambiente.value},
    )
    return ConexionArcaResponse.desde(conexion, _hoy())


@router_arca.post("/credenciales", response_model=ConexionArcaResponse)
async def cargar_credenciales(
    usuario: SoloAdmin,
    uc: Annotated[CargarCredencialesArca, Depends(uc_cargar_credenciales_arca)],
    audit: Auditoria,
    certificado: Annotated[UploadFile, File()],
    clave: Annotated[UploadFile, File()],
) -> ConexionArcaResponse:
    conexion = uc.execute(
        CargarCredencialesCommand(
            certificado=await certificado.read(),
            clave=await clave.read(),
            usuario_id=usuario.id,
        )
    )
    audit.execute(
        usuario,
        accion="cargar_certificado",
        entidad="conexion_arca",
        entidad_id=conexion.id,
        detalle=f"vence={conexion.certificado_vence}",
    )
    return ConexionArcaResponse.desde(conexion, _hoy())


@router_arca.post("/probar", response_model=PruebaArcaResponse)
def probar_conexion(
    usuario: SoloAdmin,
    uc: Annotated[ProbarConexionArca, Depends(uc_probar_conexion_arca)],
    obtener: Annotated[ObtenerConexionArca, Depends(uc_obtener_conexion_arca)],
    audit: Auditoria,
) -> PruebaArcaResponse:
    try:
        datos = uc.execute()
    except ServicioExternoNoDisponible as e:
        resultado = PruebaArcaResponse(ok=False, mensaje=e.message)
    else:
        resultado = PruebaArcaResponse(
            ok=True,
            mensaje="Conexión correcta: ARCA respondió con los datos del certificado",
            datos=SugerenciaPadronResponse.desde(datos, _hoy()) if datos else None,
        )
    audit.execute(
        usuario,
        accion="probar",
        entidad="conexion_arca",
        entidad_id=obtener.execute().id,
        detalle="ok" if resultado.ok else f"error: {resultado.mensaje[:200]}",
    )
    return resultado

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from taller.adapters.inbound.api.deps import get_current_user, require_roles
from taller.adapters.inbound.api.deps_auditoria import uc_registrar_auditoria
from taller.adapters.inbound.api.deps_configuracion import (
    uc_determinar_tipo,
    uc_guardar_configuracion,
    uc_obtener_configuracion,
)
from taller.adapters.inbound.api.schemas_configuracion import (
    ConfiguracionCreate,
    ConfiguracionResponse,
    TipoComprobanteResponse,
)
from taller.application.use_cases.auditoria import RegistrarAuditoria
from taller.application.use_cases.configuracion import (
    DeterminarTipoCommand,
    DeterminarTipoComprobante,
    GuardarConfiguracion,
    GuardarConfiguracionCommand,
    ObtenerConfiguracion,
)
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.enums import CondicionIva

Lector = Annotated[Usuario, Depends(get_current_user)]
SoloAdmin = Annotated[Usuario, Depends(require_roles(Rol.ADMIN))]

router = APIRouter(prefix="/configuracion-taller", tags=["configuracion"])


@router.get("", response_model=ConfiguracionResponse | None)
def obtener_configuracion(
    _: Lector,
    uc: Annotated[ObtenerConfiguracion, Depends(uc_obtener_configuracion)],
) -> ConfiguracionResponse | None:
    # Sin configurar devuelve null: el frontend guía la carga inicial (H1).
    try:
        return ConfiguracionResponse.from_domain(uc.execute())
    except Exception:
        return None


@router.put("", response_model=ConfiguracionResponse)
def guardar_configuracion(
    usuario: SoloAdmin,
    payload: ConfiguracionCreate,
    uc: Annotated[GuardarConfiguracion, Depends(uc_guardar_configuracion)],
    audit: Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)],
) -> ConfiguracionResponse:
    cmd = GuardarConfiguracionCommand(
        razon_social=payload.razon_social,
        cuit=payload.cuit,
        cond_iva=payload.cond_iva,
        domicilio_fiscal=payload.domicilio_fiscal,
        inicio_actividades=payload.inicio_actividades,
        puntos_venta=tuple(p.numero for p in payload.puntos_venta),
    )
    config = uc.execute(cmd)
    audit.execute(
        usuario,
        accion="configurar",
        entidad="configuracion_taller",
        entidad_id=config.id,
        detalle=f"cond_iva={config.cond_iva.value}, cuit={config.cuit}",
        datos_despues={
            "razon_social": config.razon_social,
            "cond_iva": config.cond_iva.value,
            "cond_iva_desde": str(config.cond_iva_desde or ""),
            "puntos_venta": [p.numero for p in config.puntos_venta],
        },
    )
    return ConfiguracionResponse.from_domain(config)


@router.get("/tipo-comprobante", response_model=TipoComprobanteResponse)
def determinar_tipo_comprobante(
    _: Lector,
    uc: Annotated[DeterminarTipoComprobante, Depends(uc_determinar_tipo)],
    cond_receptor: Annotated[CondicionIva, Query()],
) -> TipoComprobanteResponse:
    tipo = uc.execute(DeterminarTipoCommand(cond_receptor=cond_receptor))
    return TipoComprobanteResponse(tipo=tipo)

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from taller.domain.entities.conexion_arca import AmbienteArca, ConexionArca
from taller.domain.enums import CondicionIva, TipoPersona
from taller.domain.ports.padron import DatosPadron

_BASE = ConfigDict(extra="forbid")


class SugerenciaPadronResponse(BaseModel):
    """Sugerencia del padrón: **no se guarda sola**, alimenta el formulario."""

    cuit: str
    fuente: str
    razon_social: str | None
    cond_iva: CondicionIva | None
    cond_iva_texto: str | None
    direccion: str | None
    tipo_persona: TipoPersona | None
    estado: str | None
    consultado_en: date

    @classmethod
    def desde(cls, d: DatosPadron, hoy: date) -> SugerenciaPadronResponse:
        return cls(
            cuit=d.cuit,
            fuente=d.fuente,
            razon_social=d.razon_social,
            cond_iva=d.cond_iva,
            cond_iva_texto=d.cond_iva_texto,
            direccion=d.direccion,
            tipo_persona=d.tipo_persona,
            estado=d.estado,
            consultado_en=hoy,
        )


class EstadoPadronResponse(BaseModel):
    """Para cualquier usuario: si mostrar el botón «Buscar en ARCA» en los formularios."""

    disponible: bool


class ConexionArcaUpdate(BaseModel):
    model_config = _BASE
    activa: bool
    ambiente: AmbienteArca
    cuit: str | None = None


class ConexionArcaResponse(BaseModel):
    """Nunca incluye la clave privada ni el contenido del certificado."""

    activa: bool
    ambiente: AmbienteArca
    cuit: str | None
    tiene_credenciales: bool
    certificado_sujeto: str | None
    certificado_vence: date | None
    certificado_vencido: bool
    lista_para_usar: bool
    actualizado_en: datetime | None

    @classmethod
    def desde(cls, c: ConexionArca, hoy: date) -> ConexionArcaResponse:
        return cls(
            activa=c.activa,
            ambiente=c.ambiente,
            cuit=str(c.cuit) if c.cuit else None,
            tiene_credenciales=c.tiene_credenciales,
            certificado_sujeto=c.certificado_sujeto,
            certificado_vence=c.certificado_vence,
            certificado_vencido=c.certificado_vencido(hoy),
            lista_para_usar=c.lista_para_usar(hoy),
            actualizado_en=c.actualizado_en,
        )


class PruebaArcaResponse(BaseModel):
    ok: bool
    mensaje: str
    datos: SugerenciaPadronResponse | None = None

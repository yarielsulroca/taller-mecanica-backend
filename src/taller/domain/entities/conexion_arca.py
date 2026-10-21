from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from taller.domain.exceptions import Conflicto
from taller.domain.value_objects.cuit import Cuit


class AmbienteArca(StrEnum):
    HOMOLOGACION = "homologacion"
    PRODUCCION = "produccion"


@dataclass(slots=True)
class ConexionArca:
    """Conexión opcional con los web services oficiales de ARCA (fila única).

    **Apagada por defecto**: los datos fiscales de clientes y proveedores se cargan
    a mano. Si el taller la activa, la app *sugiere* razón social y condición IVA
    a partir del CUIT; el operador siempre confirma antes de guardar.
    """

    id: UUID = field(default_factory=uuid4)
    activa: bool = False
    ambiente: AmbienteArca = AmbienteArca.PRODUCCION
    cuit: Cuit | None = None
    tiene_credenciales: bool = False
    certificado_sujeto: str | None = None
    certificado_vence: date | None = None
    actualizado_en: datetime | None = None
    actualizado_por: UUID | None = None

    def certificado_vencido(self, hoy: date) -> bool:
        return self.certificado_vence is not None and self.certificado_vence < hoy

    def lista_para_usar(self, hoy: date) -> bool:
        return (
            self.activa
            and self.tiene_credenciales
            and self.cuit is not None
            and not self.certificado_vencido(hoy)
        )

    def configurar(
        self,
        *,
        activa: bool,
        ambiente: AmbienteArca,
        cuit: Cuit | None,
        hoy: date,
    ) -> None:
        self.ambiente = ambiente
        self.cuit = cuit
        if activa:
            self._validar_activable(hoy)
        self.activa = activa

    def registrar_credenciales(
        self, *, sujeto: str, vence: date, cuit: Cuit | None
    ) -> None:
        self.tiene_credenciales = True
        self.certificado_sujeto = sujeto
        self.certificado_vence = vence
        if cuit is not None:
            self.cuit = cuit

    def _validar_activable(self, hoy: date) -> None:
        if not self.tiene_credenciales:
            raise Conflicto(
                "Para activar la conexión con ARCA primero cargá el certificado y la clave"
            )
        if self.cuit is None:
            raise Conflicto("Indicá el CUIT a nombre del cual se emitió el certificado")
        if self.certificado_vencido(hoy):
            raise Conflicto(
                f"El certificado venció el {self.certificado_vence}; generá uno nuevo en ARCA"
            )

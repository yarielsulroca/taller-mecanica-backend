from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from taller.domain.entities.configuracion import (
    ConfiguracionTaller,
    PuntoVentaTaller,
    determinar_tipo_comprobante,
)
from taller.domain.enums import CondicionIva, TipoComprobante
from taller.domain.exceptions import NoEncontrado
from taller.domain.ports.configuracion import ConfiguracionTallerRepository
from taller.domain.value_objects.cuit import Cuit


class ObtenerConfiguracion:
    def __init__(self, repo: ConfiguracionTallerRepository) -> None:
        self._repo = repo

    def execute(self) -> ConfiguracionTaller:
        configuracion = self._repo.obtener()
        if configuracion is None:
            raise NoEncontrado(
                "El taller no está configurado: cargá razón social, CUIT y condición IVA"
            )
        return configuracion


@dataclass(frozen=True, slots=True)
class GuardarConfiguracionCommand:
    razon_social: str
    cuit: str
    cond_iva: CondicionIva
    domicilio_fiscal: str | None = None
    inicio_actividades: date | None = None
    puntos_venta: tuple[int, ...] = ()


class GuardarConfiguracion:
    """Crea o actualiza la identidad fiscal del taller (H1).

    Si cambia la condición IVA se registra la fecha desde la que rige (libro IVA).
    Los puntos de venta se sincronizan: crecer no exige tocar código.
    """

    def __init__(self, repo: ConfiguracionTallerRepository) -> None:
        self._repo = repo

    def execute(self, cmd: GuardarConfiguracionCommand) -> ConfiguracionTaller:
        cuit = Cuit(cmd.cuit)
        existente = self._repo.obtener()
        cond_iva = cmd.cond_iva
        cond_iva_desde = cmd.inicio_actividades
        if existente is not None:
            cambio = cond_iva != existente.cond_iva
            cond_iva_desde = cmd.inicio_actividades if cambio else existente.cond_iva_desde

        configuracion = ConfiguracionTaller(
            id=existente.id if existente is not None else uuid4(),
            razon_social=cmd.razon_social.strip(),
            cuit=cuit,
            cond_iva=cond_iva,
            cond_iva_desde=cond_iva_desde,
            domicilio_fiscal=cmd.domicilio_fiscal,
            inicio_actividades=cmd.inicio_actividades,
        )
        for numero in dict.fromkeys(cmd.puntos_venta):  # sin duplicados, conserva orden
            configuracion.puntos_venta.append(PuntoVentaTaller(numero=numero))
        self._repo.guardar(configuracion)
        return configuracion


@dataclass(frozen=True, slots=True)
class DeterminarTipoCommand:
    cond_receptor: CondicionIva


class DeterminarTipoComprobante:
    """Devuelve el tipo A/B/C que corresponde para el taller según su condición IVA."""

    def __init__(self, repo: ConfiguracionTallerRepository) -> None:
        self._repo = repo

    def execute(self, cmd: DeterminarTipoCommand) -> TipoComprobante:
        configuracion = self._repo.obtener()
        if configuracion is None:
            raise NoEncontrado("El taller no está configurado: cargá la condición IVA del emisor")
        return determinar_tipo_comprobante(configuracion.cond_iva, cmd.cond_receptor)

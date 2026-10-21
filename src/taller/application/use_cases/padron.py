from __future__ import annotations

import logging
from dataclasses import dataclass

from taller.domain.exceptions import ServicioExternoNoDisponible
from taller.domain.ports.padron import DatosPadron, Padron
from taller.domain.value_objects.cuit import Cuit

_log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SugerirCommand:
    cuit: str


class SugerirPorCuit:
    """Autocompleta los datos de un tercero o del taller a partir del CUIT.

    Devuelve una **sugerencia** (o null). El operador confirma y corrige en el
    formulario antes de guardar — la API jamás escribe con estos datos solos.
    Sin conexión con ARCA activa (por defecto) devuelve null: carga manual.
    """

    def __init__(self, padron: Padron | None) -> None:
        self._padron = padron

    def execute(self, cmd: SugerirCommand) -> DatosPadron | None:
        cuit = Cuit(cmd.cuit)  # dígito verificador: 422 si el CUIT no existe
        if self._padron is None:
            return None
        try:
            return self._padron.consultar(str(cuit))
        except ServicioExternoNoDisponible as e:
            _log.warning("Padrón ARCA no disponible: %s", e.message)
            return None

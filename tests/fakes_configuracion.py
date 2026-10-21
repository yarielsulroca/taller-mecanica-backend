from __future__ import annotations

from taller.domain.entities.configuracion import ConfiguracionTaller


class FakeConfiguracionTallerRepository:
    """Fila única en memoria."""

    def __init__(self, configuracion: ConfiguracionTaller | None = None) -> None:
        self._configuracion = configuracion

    def obtener(self) -> ConfiguracionTaller | None:
        return self._configuracion

    def guardar(self, configuracion: ConfiguracionTaller) -> None:
        self._configuracion = configuracion

    def hay_configuracion(self) -> bool:
        return self._configuracion is not None

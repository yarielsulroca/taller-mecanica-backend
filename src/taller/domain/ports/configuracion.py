from __future__ import annotations

from typing import Protocol

from taller.domain.entities.configuracion import ConfiguracionTaller


class ConfiguracionTallerRepository(Protocol):
    def obtener(self) -> ConfiguracionTaller | None: ...
    def guardar(self, configuracion: ConfiguracionTaller) -> None: ...
    def hay_configuracion(self) -> bool: ...

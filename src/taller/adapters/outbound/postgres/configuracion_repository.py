from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import (
    ConfiguracionTallerORM,
    PuntoVentaTallerORM,
)
from taller.domain.entities.configuracion import ConfiguracionTaller, PuntoVentaTaller
from taller.domain.enums import CondicionIva
from taller.domain.value_objects.cuit import Cuit


def _a_dominio(o: ConfiguracionTallerORM) -> ConfiguracionTaller:
    return ConfiguracionTaller(
        id=o.id,
        razon_social=o.razon_social,
        cuit=Cuit(o.cuit),
        cond_iva=CondicionIva(o.cond_iva),
        cond_iva_desde=o.cond_iva_desde,
        domicilio_fiscal=o.domicilio_fiscal,
        inicio_actividades=o.inicio_actividades,
        puntos_venta=[
            PuntoVentaTaller(id=p.id, numero=p.numero, activo=p.activo) for p in o.puntos_venta
        ],
    )


class SqlConfiguracionTallerRepository:
    """Fila única: la configuración del taller es un solo registro."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self) -> ConfiguracionTaller | None:
        orm = self._s.scalars(select(ConfiguracionTallerORM).limit(1)).first()
        return _a_dominio(orm) if orm is not None else None

    def hay_configuracion(self) -> bool:
        return self._s.scalars(select(ConfiguracionTallerORM.id).limit(1)).first() is not None

    def guardar(self, configuracion: ConfiguracionTaller) -> None:
        orm = self._s.get(ConfiguracionTallerORM, configuracion.id)
        if orm is None:
            orm = ConfiguracionTallerORM(id=configuracion.id)
            self._s.add(orm)
        orm.razon_social = configuracion.razon_social
        orm.cuit = str(configuracion.cuit)
        orm.cond_iva = configuracion.cond_iva.value
        orm.cond_iva_desde = configuracion.cond_iva_desde
        orm.domicilio_fiscal = configuracion.domicilio_fiscal
        orm.inicio_actividades = configuracion.inicio_actividades

        por_numero = {p.numero: p for p in orm.puntos_venta}
        deseados = {p.numero for p in configuracion.puntos_venta}
        for existente in [p for p in orm.puntos_venta if p.numero not in deseados]:
            orm.puntos_venta.remove(existente)
        for punto in configuracion.puntos_venta:
            fila = por_numero.get(punto.numero)
            if fila is None:
                fila = PuntoVentaTallerORM(
                    id=punto.id, configuracion_id=configuracion.id, numero=punto.numero
                )
                orm.puntos_venta.append(fila)
            fila.activo = punto.activo
        self._s.flush()

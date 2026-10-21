from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from taller.domain.entities.base import Maestro
from taller.domain.enums import PeriodicidadPago, TipoRemuneracion
from taller.domain.exceptions import SolicitudInvalida

_CENTAVOS = Decimal("0.01")
HORAS_JORNADA = Decimal("8")


def _pesos(valor: Decimal | None, nombre: str) -> Decimal | None:
    if valor is None:
        return None
    if valor < 0:
        raise SolicitudInvalida(f"El {nombre} no puede ser negativo")
    return valor.quantize(_CENTAVOS)


@dataclass(slots=True, kw_only=True)
class Trabajador(Maestro):
    """Cada tipo de remuneración usa un solo dato; los otros quedan vacíos.

    - sueldo: `monto_periodo`, pesos fijos por cada período de `periodicidad_pago`.
    - jornal: `valor_hora`, en pesos; la jornada es de `HORAS_JORNADA` horas.
    - comisión (dueños): `porcentaje_comision` sobre la ganancia del período.
    """

    nombre: str
    rol: str
    tipo_remuneracion: TipoRemuneracion
    periodicidad_pago: PeriodicidadPago = PeriodicidadPago.MENSUAL
    monto_periodo: Decimal | None = None
    valor_hora: Decimal | None = None
    porcentaje_comision: Decimal | None = None

    def __post_init__(self) -> None:
        self.definir_remuneracion(
            self.tipo_remuneracion,
            monto_periodo=self.monto_periodo,
            valor_hora=self.valor_hora,
            porcentaje_comision=self.porcentaje_comision,
        )

    def definir_remuneracion(
        self,
        tipo: TipoRemuneracion,
        *,
        monto_periodo: Decimal | None = None,
        valor_hora: Decimal | None = None,
        porcentaje_comision: Decimal | None = None,
    ) -> None:
        self.tipo_remuneracion = tipo
        self.monto_periodo = None
        self.valor_hora = None
        self.porcentaje_comision = None
        if tipo is TipoRemuneracion.SUELDO:
            self.monto_periodo = _pesos(monto_periodo, "monto por período")
        elif tipo is TipoRemuneracion.JORNAL:
            self.valor_hora = _pesos(valor_hora, "valor por hora")
        elif porcentaje_comision is not None:
            if not Decimal("0") < porcentaje_comision <= Decimal("100"):
                raise SolicitudInvalida("El porcentaje de comisión debe ser mayor a 0 y hasta 100")
            self.porcentaje_comision = porcentaje_comision.quantize(_CENTAVOS)

    @property
    def valor_jornada(self) -> Decimal | None:
        if self.valor_hora is None:
            return None
        return (self.valor_hora * HORAS_JORNADA).quantize(_CENTAVOS)

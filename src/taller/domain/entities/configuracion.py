from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from taller.domain.enums import CondicionIva, TipoComprobante
from taller.domain.exceptions import Conflicto, SolicitudInvalida
from taller.domain.value_objects.cuit import Cuit

_MONOTRIBUTISTAS = frozenset(
    {
        CondicionIva.MONOTRIBUTO,
        CondicionIva.MONOTRIBUTISTA_SOCIAL,
        CondicionIva.MONOTRIBUTISTA_INDEPENDIENTE_PROMOVIDO,
        CondicionIva.NO_CATEGORIZADO,
        CondicionIva.PROVEEDOR_EXTERIOR,
    }
)
_SIN_DISCRIMINACION = frozenset(
    {CondicionIva.EXENTO, CondicionIva.IVA_NO_ALCANZADO, CondicionIva.IVA_LIBERADO_LEY_19640}
)
_TIPOS_FISCALES_ABC = frozenset(
    {
        TipoComprobante.FACTURA_A,
        TipoComprobante.FACTURA_B,
        TipoComprobante.FACTURA_C,
    }
)


@dataclass(slots=True)
class PuntoVentaTaller:
    """Punto de venta habilitado. El taller crece: se agregan sin tocar código."""

    numero: int
    id: UUID = field(default_factory=uuid4)
    activo: bool = True

    def __post_init__(self) -> None:
        if self.numero <= 0:
            raise SolicitudInvalida("El punto de venta debe ser mayor a cero")


@dataclass(slots=True)
class ConfiguracionTaller:
    """Identidad fiscal del taller (fila única): H1.

    Diseño pensado para **crecer con el taller**:

    - La **condición IVA se configura a mano** (el dueño la conoce); la app deriva
      A/B/C, impuestos y reportes de esa condición (H2). Si pasa de monotributo a
      Responsable Inscripto, basta cambiarla acá con la **fecha desde** la que rige
      para el libro IVA.
    - Los **puntos de venta** son una lista: hoy uno, mañana tres, sin tocar código.
    - La **numeración fiscal** es correlativa por (punto de venta, tipo de comprobante).
    """

    razon_social: str
    cuit: Cuit
    cond_iva: CondicionIva
    id: UUID = field(default_factory=uuid4)
    cond_iva_desde: date | None = None
    domicilio_fiscal: str | None = None
    inicio_actividades: date | None = None
    puntos_venta: list[PuntoVentaTaller] = field(default_factory=list)

    def cambiar_condicion_iva(self, cond_iva: CondicionIva, desde: date) -> None:
        """El taller crece: monotributo → Responsable Inscripto con un solo cambio."""
        if cond_iva != self.cond_iva:
            self.cond_iva = cond_iva
            self.cond_iva_desde = desde

    def agregar_punto_venta(self, numero: int) -> PuntoVentaTaller:
        if any(p.numero == numero for p in self.puntos_venta):
            raise Conflicto(f"El punto de venta {numero} ya está configurado")
        punto = PuntoVentaTaller(numero=numero)
        self.puntos_venta.append(punto)
        return punto

    def punto_venta_habilitado(self, numero: int | None) -> bool:
        """Sin puntos cargados se permite cualquier número (compatibilidad); con la
        lista cargada, sólo se aceptan puntos de venta activos."""
        if numero is None:
            return True
        if not self.puntos_venta:
            return True
        return any(p.numero == numero and p.activo for p in self.puntos_venta)

    def validar_punto_venta(self, numero: int | None) -> None:
        if not self.punto_venta_habilitado(numero):
            raise Conflicto(
                f"El punto de venta {numero} no está habilitado para el taller",
                details={"puntos_habilitados": [p.numero for p in self.puntos_venta if p.activo]},
            )


def determinar_tipo_comprobante(
    cond_emisor: CondicionIva, cond_receptor: CondicionIva
) -> TipoComprobante:
    """Regla A/B/C (RN-050 / H2): depende del **emisor** (taller) y del receptor.

    - Monotributo (y similares sin IVA) → **C** siempre.
    - Exento / No Alcanzado / Liberado → **B** (no discrimina IVA).
    - Responsable Inscripto → **A** si el receptor es RI; **B** para el resto.
    """
    if cond_emisor in _MONOTRIBUTISTAS:
        return TipoComprobante.FACTURA_C
    if cond_emisor in _SIN_DISCRIMINACION:
        return TipoComprobante.FACTURA_B
    if cond_emisor == CondicionIva.RESPONSABLE_INSCRIPTO:
        if cond_receptor == CondicionIva.RESPONSABLE_INSCRIPTO:
            return TipoComprobante.FACTURA_A
        return TipoComprobante.FACTURA_B
    return TipoComprobante.FACTURA_C


def validar_tipo_comprobante(
    cond_emisor: CondicionIva, cond_receptor: CondicionIva, tipo: TipoComprobante
) -> None:
    """Valida que el tipo A/B/C cargado corresponda (RN-050 / H2). Nunca autocorrige."""
    if tipo not in _TIPOS_FISCALES_ABC:
        return
    esperado = determinar_tipo_comprobante(cond_emisor, cond_receptor)
    if tipo != esperado:
        raise SolicitudInvalida(
            f"Para emisor {cond_emisor.value} y receptor {cond_receptor.value} "
            f"corresponde comprobante {esperado.value}, no {tipo.value}",
            details={"esperado": esperado.value, "cargado": tipo.value},
        )

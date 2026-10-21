from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from taller.application.use_cases.notificar_ot import ROLES_COBRANZA, pesos
from taller.domain.entities.notificacion import Notificacion
from taller.domain.entities.usuario import Rol
from taller.domain.enums import (
    EstadoComprobante,
    EstadoCuota,
    OrigenCuota,
    Severidad,
    TipoNotificacion,
)
from taller.domain.ports import Clock
from taller.domain.ports.finanzas import CuotaRepository
from taller.domain.ports.notificaciones import NotificacionRepository, Notificador
from taller.domain.ports.repositories import ComprobanteRepository


@dataclass(frozen=True, slots=True)
class ResultadoCumplimiento:
    cuotas_vencidas: int
    comprobantes_pendientes: int


class EjecutarChequeosCumplimiento:
    """Job asincrónico: notifica vencimientos y comprobantes pendientes (RN-118).

    Idempotente: las cuotas se notifican sólo al pasar a `vencida` y los comprobantes
    sólo una vez (se chequea que no exista la notificación).
    """

    def __init__(
        self,
        cuotas: CuotaRepository,
        comprobantes: ComprobanteRepository,
        notificaciones: NotificacionRepository,
        notificador: Notificador,
        clock: Clock,
        dias_comprobante: int = 3,
    ) -> None:
        self._cuotas = cuotas
        self._comprobantes = comprobantes
        self._notificaciones = notificaciones
        self._notificador = notificador
        self._clock = clock
        self._dias = dias_comprobante

    def execute(self) -> ResultadoCumplimiento:
        hoy = self._clock.ahora().date()
        cuotas_vencidas = self._procesar_cuotas(hoy)
        comprobantes = self._procesar_comprobantes(hoy)
        return ResultadoCumplimiento(
            cuotas_vencidas=cuotas_vencidas, comprobantes_pendientes=comprobantes
        )

    def _procesar_cuotas(self, hoy: date) -> int:
        vencidas = 0
        for cuota in self._cuotas.listar_impagas():
            if cuota.fecha_vencimiento >= hoy or cuota.estado == EstadoCuota.VENCIDA:
                continue
            cuota.marcar_vencida(hoy)
            self._cuotas.guardar(cuota)
            vencidas += 1
            que = "cobrar" if cuota.origen == OrigenCuota.COBRO else "pagar"
            detalle = f" ({cuota.notas})" if cuota.notas else ""
            for rol in ROLES_COBRANZA:
                self._notificador.notificar(
                    Notificacion(
                        tipo=TipoNotificacion.CUOTA_VENCIDA,
                        titulo=f"Vencido sin {que}{detalle}: {pesos(cuota.saldo)}",
                        mensaje=(
                            f"Cuota #{cuota.numero} vencida el "
                            f"{cuota.fecha_vencimiento.strftime('%d/%m/%Y')}; "
                            f"falta {que} {pesos(cuota.saldo)}."
                        ),
                        severidad=Severidad.ADVERTENCIA,
                        referencia_tipo="cuota",
                        referencia_id=cuota.id,
                        rol_destino=rol,
                        creada_en=self._clock.ahora(),
                    )
                )
        return vencidas

    def _procesar_comprobantes(self, hoy: date) -> int:
        pendientes = 0
        for comprobante in self._comprobantes.listar(estado=EstadoComprobante.PENDIENTE):
            if (hoy - comprobante.fecha).days < self._dias:
                continue
            if self._notificaciones.existe(
                referencia_tipo="comprobante",
                referencia_id=comprobante.id,
                tipo=TipoNotificacion.FACTURA_PENDIENTE,
            ):
                continue
            pendientes += 1
            self._notificador.notificar(
                Notificacion(
                    tipo=TipoNotificacion.FACTURA_PENDIENTE,
                    titulo="Comprobante pendiente de aprobación",
                    mensaje=(
                        f"El comprobante {comprobante.tipo.value} del "
                        f"{comprobante.fecha.isoformat()} sigue pendiente de aprobación."
                    ),
                    severidad=Severidad.ADVERTENCIA,
                    referencia_tipo="comprobante",
                    referencia_id=comprobante.id,
                    rol_destino=Rol.ADMINISTRACION,
                    creada_en=self._clock.ahora(),
                )
            )
        return pendientes

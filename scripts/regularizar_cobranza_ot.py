"""Abre la cuenta por cobrar de las OT que ya estaban en `pendiente_pago` (RN-133).

Idempotente: sólo toca las OT sin cuota de cobro impaga. Uso:
    .venv\\Scripts\\python scripts\\regularizar_cobranza_ot.py
"""
from __future__ import annotations

from taller.adapters.outbound.postgres.finanzas_repository import (
    SqlCuotaRepository,
    SqlMovimientoRepository,
)
from taller.adapters.outbound.postgres.notificaciones_repository import (
    SqlNotificacionRepository,
)
from taller.adapters.outbound.postgres.ordenes_repository import SqlOrdenTrabajoRepository
from taller.adapters.outbound.realtime.bus import BusEnMemoria
from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
from taller.application.use_cases.cobranza_ot import CobranzaOT
from taller.application.use_cases.notificar_ot import NotificacionesOT
from taller.container import build_container
from taller.domain.enums import EstadoOT, OrigenCuota

container = build_container()
session = container.session_factory()
try:
    ordenes = SqlOrdenTrabajoRepository(session)
    cuotas = SqlCuotaRepository(session)
    notifs = SqlNotificacionRepository(session)
    avisos = NotificacionesOT(NotificadorRepoBus(notifs, BusEnMemoria()), notifs, container.clock)
    cobranza = CobranzaOT(ordenes, cuotas, SqlMovimientoRepository(session), container.clock, avisos)
    for ot in ordenes.listar(estado=EstadoOT.PENDIENTE_PAGO):
        abiertas = [
            c for c in cuotas.listar(origen=OrigenCuota.COBRO, referencia_id=ot.id) if c.impaga
        ]
        if abiertas:
            print(f"{ot.codigo}: ya tenía cuenta por cobrar")
            continue
        saldo = cobranza.abrir_cuenta(ot)
        if saldo <= 0 and cobranza.cerrar_si_saldada(ot.id):
            print(f"{ot.codigo}: ya estaba cobrada, pasó a cobrado")
        else:
            print(f"{ot.codigo}: por cobrar {saldo}")
    session.commit()
finally:
    session.close()

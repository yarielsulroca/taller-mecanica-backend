from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from taller.adapters.inbound.api.error_handlers import registrar_error_handlers
from taller.adapters.inbound.api.middleware_auditoria import registrar_middleware_auditoria
from taller.adapters.inbound.api.routers import (
    accesos,
    auditoria,
    auth,
    cobros,
    compras,
    comprobantes,
    configuracion,
    finanzas,
    health,
    maestros,
    notificaciones,
    ordenes,
    padron,
    pagos,
    texto,
    vencimientos,
)
from taller.adapters.outbound.realtime.bus import BusDiferido
from taller.container import Container, build_container

logger = logging.getLogger(__name__)


def _ejecutar_cumplimiento(container: Container) -> None:
    """Corre el job de cumplimiento con una sesión propia (fuera del event loop)."""
    from taller.adapters.outbound.postgres.comprobantes_repository import (
        SqlComprobanteRepository,
    )
    from taller.adapters.outbound.postgres.finanzas_repository import SqlCuotaRepository
    from taller.adapters.outbound.postgres.notificaciones_repository import (
        SqlNotificacionRepository,
    )
    from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
    from taller.application.use_cases.cumplimiento import EjecutarChequeosCumplimiento

    session = container.session_factory()
    bus = BusDiferido(container.bus)
    try:
        repo_notif = SqlNotificacionRepository(session)
        use_case = EjecutarChequeosCumplimiento(
            SqlCuotaRepository(session),
            SqlComprobanteRepository(session),
            repo_notif,
            NotificadorRepoBus(repo_notif, bus),
            container.clock,
            container.settings.comprobante_pendiente_dias,
        )
        use_case.execute()
        session.commit()
        bus.liberar()
    except Exception:
        session.rollback()
        logger.exception("Falló el job de cumplimiento")
    finally:
        session.close()


def _ejecutar_vencimientos(container: Container) -> None:
    """Genera vencimientos de gastos fijos y sueldos y re-lanza sus avisos."""
    from taller.adapters.outbound.postgres.maestros_repositories import (
        SqlTrabajadorRepository,
    )
    from taller.adapters.outbound.postgres.notificaciones_repository import (
        SqlNotificacionRepository,
    )
    from taller.adapters.outbound.postgres.pagos_repository import SqlLiquidacionRepository
    from taller.adapters.outbound.postgres.vencimientos_repository import (
        SqlGastoFijoRepository,
        SqlObligacionRepository,
    )
    from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
    from taller.application.use_cases.vencimientos import (
        EjecutarVencimientos,
        GenerarObligaciones,
        RecordarVencimientos,
    )

    session = container.session_factory()
    bus = BusDiferido(container.bus)
    try:
        obligaciones = SqlObligacionRepository(session)
        repo_notif = SqlNotificacionRepository(session)
        EjecutarVencimientos(
            GenerarObligaciones(
                SqlGastoFijoRepository(session),
                SqlTrabajadorRepository(session),
                SqlLiquidacionRepository(session),
                obligaciones,
                container.clock,
            ),
            RecordarVencimientos(
                obligaciones, repo_notif, NotificadorRepoBus(repo_notif, bus), container.clock
            ),
        ).execute()
        session.commit()
        bus.liberar()
    except Exception:
        session.rollback()
        logger.exception("Falló el job de vencimientos")
    finally:
        session.close()


async def _bucle_cumplimiento(container: Container) -> None:
    intervalo = max(1, container.settings.cumplimiento_minutos) * 60
    while True:
        await asyncio.to_thread(_ejecutar_cumplimiento, container)
        await asyncio.to_thread(_ejecutar_vencimientos, container)
        await asyncio.sleep(intervalo)


def create_app(container: Container | None = None) -> FastAPI:
    container = container or build_container()

    @asynccontextmanager
    async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
        container.bus.registrar_loop(asyncio.get_running_loop())
        tarea: asyncio.Task[None] | None = None
        if container.settings.cumplimiento_activo:
            tarea = asyncio.create_task(_bucle_cumplimiento(container))
        try:
            yield
        finally:
            if tarea is not None:
                tarea.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await tarea

    app = FastAPI(
        title=container.settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    registrar_error_handlers(app)

    registrar_middleware_auditoria(app)

    app.include_router(health.router)
    app.include_router(auth.router, prefix=container.settings.api_prefix)
    app.include_router(accesos.router, prefix=container.settings.api_prefix)
    app.include_router(maestros.router, prefix=container.settings.api_prefix)
    app.include_router(ordenes.router, prefix=container.settings.api_prefix)
    app.include_router(comprobantes.router, prefix=container.settings.api_prefix)
    app.include_router(notificaciones.router, prefix=container.settings.api_prefix)
    app.include_router(texto.router, prefix=container.settings.api_prefix)
    app.include_router(auditoria.router, prefix=container.settings.api_prefix)
    app.include_router(finanzas.router, prefix=container.settings.api_prefix)
    app.include_router(compras.router, prefix=container.settings.api_prefix)
    app.include_router(cobros.router, prefix=container.settings.api_prefix)
    app.include_router(pagos.router, prefix=container.settings.api_prefix)
    app.include_router(vencimientos.router, prefix=container.settings.api_prefix)
    app.include_router(configuracion.router, prefix=container.settings.api_prefix)
    app.include_router(padron.router, prefix=container.settings.api_prefix)
    app.include_router(padron.router_arca, prefix=container.settings.api_prefix)

    return app

"""Middleware de auditoría de operaciones (pack admin local).

Registra **toda escritura** (POST/PATCH/PUT/DELETE) contra la API con:
usuario · operación · ruta · resultado · duración. Las lecturas (GET) no se
auditan: no aportan trazabilidad y su volumen entorpecería la app sin valor.

El insert corre en un `try/except` aislado con sesión propia: si la auditoría
falla (p. ej. DB saturada), la operación original **nunca se rompe**.
"""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request, Response

from taller.adapters.outbound.postgres.auditoria_repository import SqlAuditoriaRepository
from taller.adapters.outbound.postgres.usuario_repository import SqlUsuarioRepository
from taller.application.use_cases.auditoria import RegistrarAuditoria


def registrar_middleware_auditoria(app: FastAPI) -> None:
    container = app.state.container
    prefix = container.settings.api_prefix

    @app.middleware("http")
    async def auditar_escrituras(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        metodo = request.method.upper()
        ruta = request.url.path
        auditable = (
            metodo in {"POST", "PATCH", "PUT", "DELETE"}
            and ruta.startswith(prefix)
            and "/notificaciones/stream" not in ruta
        )
        inicio = time.perf_counter()
        respuesta = await call_next(request)
        if not auditable:
            return respuesta

        ms = (time.perf_counter() - inicio) * 1000
        encabezado = request.headers.get("Authorization", "")
        if not encabezado.startswith("Bearer "):
            return respuesta  # sin usuario identificado (p. ej. 401): no hay de quién
        try:
            payload = container.tokens.decodificar(encabezado.removeprefix("Bearer ").strip())
            sub = payload.get("sub")
            if not isinstance(sub, str):
                return respuesta
            usuario_id = uuid.UUID(sub)
        except Exception:
            return respuesta

        # Sesión propia: la auditoría no comparte la transacción del negocio.
        session = container.session_factory()
        try:
            usuario_repo = SqlUsuarioRepository(session)
            usuario = usuario_repo.obtener_por_id(usuario_id)
            if usuario is not None:
                segmentos = [s for s in ruta.removeprefix(prefix).strip("/").split("/") if s]
                RegistrarAuditoria(SqlAuditoriaRepository(session), container.clock).execute(
                    usuario,
                    accion=metodo.lower(),
                    entidad=(segmentos[0] if segmentos else "api"),
                    entidad_id=uuid.uuid4(),
                    detalle=f"{ruta} -> {respuesta.status_code} ({ms:.0f} ms)",
                )
                session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()
        return respuesta

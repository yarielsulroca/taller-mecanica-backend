from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from taller.domain.exceptions import DomainError


def registrar_error_handlers(app) -> None:  # type: ignore[no-untyped-def]
    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

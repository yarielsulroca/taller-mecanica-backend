from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any


class BusEnMemoria:
    """Bus de eventos en proceso para push en tiempo real (SSE).

    Publica desde código sincrónico de forma segura entre hilos; para varias
    instancias se reemplaza por un broker (Redis pub/sub) sin tocar los casos de uso.
    """

    def __init__(self) -> None:
        self._suscriptores: set[asyncio.Queue[dict[str, Any]]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def registrar_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def publicar(self, evento: dict[str, Any]) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(self._emitir, evento)

    def _emitir(self, evento: dict[str, Any]) -> None:
        for cola in list(self._suscriptores):
            cola.put_nowait(evento)

    async def suscribir(self) -> AsyncIterator[dict[str, Any]]:
        cola: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._suscriptores.add(cola)
        try:
            while True:
                yield await cola.get()
        finally:
            self._suscriptores.discard(cola)


class BusDiferido(BusEnMemoria):
    """Acumula eventos y los publica recién al confirmar la transacción.

    Evita que el navegador reciba el push y relea las notificaciones antes del commit.
    """

    def __init__(self, destino: BusEnMemoria) -> None:
        super().__init__()
        self._destino = destino
        self._pendientes: list[dict[str, Any]] = []

    def publicar(self, evento: dict[str, Any]) -> None:
        self._pendientes.append(evento)

    def liberar(self) -> None:
        for evento in self._pendientes:
            self._destino.publicar(evento)
        self._pendientes.clear()

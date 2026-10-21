from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Reloj del sistema en UTC. Se inyecta para poder testear (RA-002)."""

    def ahora(self) -> datetime:
        return datetime.now(UTC)

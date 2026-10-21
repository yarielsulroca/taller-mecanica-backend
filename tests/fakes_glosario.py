from __future__ import annotations

from taller.domain.entities.glosario import TerminoGlosario


class FakeGlosarioRepository:
    def __init__(self, terminos: list[TerminoGlosario] | None = None) -> None:
        self._items: dict[str, TerminoGlosario] = {t.clave: t for t in (terminos or [])}

    def buscar(self, *, clave_prefijo: str, limite: int = 10) -> list[TerminoGlosario]:
        items = [t for t in self._items.values() if t.activo and t.clave.startswith(clave_prefijo)]
        items.sort(key=lambda t: (-t.usos, t.termino))
        return items[:limite]

    def listar(self, *, incluir_inactivos: bool = False) -> list[TerminoGlosario]:
        return [t for t in self._items.values() if incluir_inactivos or t.activo]

    def obtener_por_clave(self, clave: str) -> TerminoGlosario | None:
        return self._items.get(clave)

    def registrar_uso(self, *, termino: str, clave: str, categoria: str | None = None) -> None:
        existente = self._items.get(clave)
        if existente is None:
            self._items[clave] = TerminoGlosario(
                termino=termino.strip(), clave=clave, categoria=categoria, usos=1
            )
        else:
            existente.usos += 1

    def guardar(self, termino: TerminoGlosario) -> None:
        self._items[termino.clave] = termino

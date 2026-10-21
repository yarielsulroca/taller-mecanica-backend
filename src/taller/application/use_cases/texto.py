from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from taller.domain.ports.glosario import GlosarioRepository

_RE_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}")


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos, espacios colapsados (para comparar)."""
    texto = " ".join(texto.strip().lower().split())
    sin_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c))


def distancia(a: str, b: str) -> int:
    """Distancia de Levenshtein (sin dependencias)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previa = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        actual = [i]
        for j, cb in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + (ca != cb)))
        previa = actual
    return previa[-1]


def _umbral(palabra: str) -> int:
    return 1 if len(palabra) <= 5 else 2


class SugerirTerminos:
    """Autocompletado por prefijo, ordenado por frecuencia de uso."""

    def __init__(self, repo: GlosarioRepository) -> None:
        self._repo = repo

    def execute(self, prefijo: str, limite: int = 10) -> list[str]:
        clave = normalizar(prefijo)
        if len(clave) < 2:
            return []
        return [t.termino for t in self._repo.buscar(clave_prefijo=clave, limite=limite)]


@dataclass(frozen=True, slots=True)
class CorreccionPalabra:
    palabra: str
    sugerencias: list[str]


@dataclass(frozen=True, slots=True)
class CorreccionTexto:
    palabras: list[CorreccionPalabra]


class CorregirTexto:
    """Sugiere correcciones para palabras que no están en el vocabulario del taller.

    Nunca reescribe solo: devuelve sugerencias para que el usuario confirme.
    """

    def __init__(self, repo: GlosarioRepository) -> None:
        self._repo = repo

    def execute(self, texto: str) -> CorreccionTexto:
        vocabulario = self._palabras()
        resultado: list[CorreccionPalabra] = []
        vistas: set[str] = set()
        for palabra in _RE_PALABRA.findall(texto):
            clave = normalizar(palabra)
            if clave in vocabulario or clave in vistas:
                continue
            vistas.add(clave)
            candidatos = self._cercanos(clave, vocabulario)
            if candidatos:
                resultado.append(CorreccionPalabra(palabra=palabra, sugerencias=candidatos))
        return CorreccionTexto(palabras=resultado)

    def _palabras(self) -> dict[str, tuple[str, int]]:
        """Vocabulario a nivel palabra (incluye las palabras de cada frase)."""
        palabras: dict[str, tuple[str, int]] = {}
        for termino in self._repo.listar():
            for palabra in _RE_PALABRA.findall(termino.termino):
                clave = normalizar(palabra)
                if clave not in palabras or termino.usos > palabras[clave][1]:
                    palabras[clave] = (palabra, termino.usos)
        return palabras

    @staticmethod
    def _cercanos(clave: str, vocabulario: dict[str, tuple[str, int]]) -> list[str]:
        umbral = _umbral(clave)
        candidatos: list[tuple[int, int, str]] = []
        for palabra_clave, (display, usos) in vocabulario.items():
            d = distancia(clave, palabra_clave)
            if d <= umbral:
                candidatos.append((d, -usos, display))
        candidatos.sort()
        return [t for _, _, t in candidatos[:3]]


class RegistrarTerminosDeTexto:
    """Aprende palabras del texto (descripciones/notas) para el autocompletado."""

    def __init__(self, repo: GlosarioRepository) -> None:
        self._repo = repo

    def execute(self, texto: str) -> None:
        for palabra in _RE_PALABRA.findall(texto):
            self._repo.registrar_uso(termino=palabra, clave=normalizar(palabra))

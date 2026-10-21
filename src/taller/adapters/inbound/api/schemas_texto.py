from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_BASE = ConfigDict(extra="forbid")


class SugerenciasResponse(BaseModel):
    sugerencias: list[str]


class RegistrarTextoRequest(BaseModel):
    model_config = _BASE
    texto: str = Field(min_length=1)


class CorregirTextoRequest(BaseModel):
    model_config = _BASE
    texto: str = Field(min_length=1)


class CorreccionPalabraResponse(BaseModel):
    palabra: str
    sugerencias: list[str]


class CorreccionResponse(BaseModel):
    palabras: list[CorreccionPalabraResponse]

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from taller.domain.entities.conexion_arca import AmbienteArca, ConexionArca
from taller.domain.exceptions import ArchivoInvalido, Conflicto
from taller.domain.ports import Clock
from taller.domain.ports.padron import (
    BovedaArca,
    ConexionArcaRepository,
    DatosPadron,
    FabricaPadronArca,
    Padron,
)
from taller.domain.value_objects.cuit import Cuit

_MAX_ARCHIVO = 64 * 1024


class ObtenerConexionArca:
    """Sin fila guardada, la conexión existe igual: apagada (carga manual)."""

    def __init__(self, repo: ConexionArcaRepository) -> None:
        self._repo = repo

    def execute(self) -> ConexionArca:
        return self._repo.obtener() or ConexionArca()


@dataclass(frozen=True, slots=True)
class GuardarConexionArcaCommand:
    activa: bool
    ambiente: AmbienteArca
    cuit: str | None
    usuario_id: UUID


class GuardarConexionArca:
    def __init__(self, repo: ConexionArcaRepository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def execute(self, cmd: GuardarConexionArcaCommand) -> ConexionArca:
        conexion = self._repo.obtener() or ConexionArca()
        ahora = self._clock.ahora()
        conexion.configurar(
            activa=cmd.activa,
            ambiente=cmd.ambiente,
            cuit=Cuit(cmd.cuit) if cmd.cuit else None,
            hoy=ahora.date(),
        )
        conexion.actualizado_en = ahora
        conexion.actualizado_por = cmd.usuario_id
        self._repo.guardar(conexion)
        return conexion


@dataclass(frozen=True, slots=True)
class CargarCredencialesCommand:
    certificado: bytes
    clave: bytes
    usuario_id: UUID


class CargarCredencialesArca:
    def __init__(self, repo: ConexionArcaRepository, boveda: BovedaArca, clock: Clock) -> None:
        self._repo = repo
        self._boveda = boveda
        self._clock = clock

    def execute(self, cmd: CargarCredencialesCommand) -> ConexionArca:
        for nombre, datos in (("certificado", cmd.certificado), ("clave", cmd.clave)):
            if not datos:
                raise ArchivoInvalido(f"Falta el archivo de {nombre}")
            if len(datos) > _MAX_ARCHIVO:
                raise ArchivoInvalido(f"El archivo de {nombre} es demasiado grande")
        info = self._boveda.guardar(cmd.certificado, cmd.clave)
        conexion = self._repo.obtener() or ConexionArca()
        conexion.registrar_credenciales(
            sujeto=info.sujeto,
            vence=info.vence,
            cuit=Cuit(info.cuit) if info.cuit else None,
        )
        conexion.actualizado_en = self._clock.ahora()
        conexion.actualizado_por = cmd.usuario_id
        self._repo.guardar(conexion)
        return conexion


class ResolverPadron:
    """El padrón ARCA sólo existe si el taller activó la conexión y está vigente."""

    def __init__(
        self,
        repo: ConexionArcaRepository,
        boveda: BovedaArca,
        fabrica: FabricaPadronArca,
        clock: Clock,
    ) -> None:
        self._repo = repo
        self._boveda = boveda
        self._fabrica = fabrica
        self._clock = clock

    def execute(self) -> Padron | None:
        conexion = self._repo.obtener()
        if conexion is None or not conexion.lista_para_usar(self._clock.ahora().date()):
            return None
        credenciales = self._boveda.leer()
        if credenciales is None:
            return None
        return self._fabrica(conexion, credenciales)


class ProbarConexionArca:
    """Consulta el propio CUIT del certificado. Se puede probar antes de activar."""

    def __init__(
        self,
        repo: ConexionArcaRepository,
        boveda: BovedaArca,
        fabrica: FabricaPadronArca,
    ) -> None:
        self._repo = repo
        self._boveda = boveda
        self._fabrica = fabrica

    def execute(self) -> DatosPadron | None:
        conexion = self._repo.obtener()
        credenciales = self._boveda.leer()
        if conexion is None or credenciales is None or not conexion.tiene_credenciales:
            raise Conflicto("Primero cargá el certificado y la clave de ARCA")
        if conexion.cuit is None:
            raise Conflicto("Indicá el CUIT a nombre del cual se emitió el certificado")
        return self._fabrica(conexion, credenciales).consultar(str(conexion.cuit))

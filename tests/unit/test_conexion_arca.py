from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from taller.application.use_cases.conexion_arca import (
    CargarCredencialesArca,
    CargarCredencialesCommand,
    GuardarConexionArca,
    GuardarConexionArcaCommand,
    ObtenerConexionArca,
    ProbarConexionArca,
    ResolverPadron,
)
from taller.domain.entities.conexion_arca import AmbienteArca, ConexionArca
from taller.domain.exceptions import ArchivoInvalido, Conflicto
from taller.domain.ports.padron import CredencialesArca, DatosPadron, InfoCertificado
from taller.domain.value_objects.cuit import Cuit
from tests.fakes import FakeClock

HOY = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
ADMIN = uuid4()
CUIT = "20123456786"


class FakeRepo:
    def __init__(self, conexion: ConexionArca | None = None) -> None:
        self.conexion = conexion

    def obtener(self) -> ConexionArca | None:
        return self.conexion

    def guardar(self, conexion: ConexionArca) -> None:
        self.conexion = conexion


class FakeBoveda:
    def __init__(self, vence: date = date(2028, 1, 1), cuit: str | None = CUIT) -> None:
        self._info = InfoCertificado(sujeto=f"CN=taller,serialNumber=CUIT {cuit}", vence=vence,
                                     cuit=cuit)
        self.guardadas: CredencialesArca | None = None

    def guardar(self, certificado: bytes, clave: bytes) -> InfoCertificado:
        self.guardadas = CredencialesArca(certificado, clave)
        return self._info

    def leer(self) -> CredencialesArca | None:
        return self.guardadas


class FakePadron:
    def __init__(self) -> None:
        self.consultados: list[str] = []

    def consultar(self, cuit: str) -> DatosPadron | None:
        self.consultados.append(cuit)
        return DatosPadron(cuit=cuit, fuente="arca", razon_social="Taller SRL")


def _fabrica(padron: FakePadron):  # type: ignore[no-untyped-def]
    def crear(conexion: ConexionArca, credenciales: CredencialesArca) -> FakePadron:
        return padron

    return crear


def _con_credenciales(repo: FakeRepo, boveda: FakeBoveda) -> None:
    CargarCredencialesArca(repo, boveda, FakeClock(HOY)).execute(
        CargarCredencialesCommand(certificado=b"cert", clave=b"key", usuario_id=ADMIN)
    )


def _activar(repo: FakeRepo, activa: bool = True, cuit: str | None = CUIT) -> ConexionArca:
    return GuardarConexionArca(repo, FakeClock(HOY)).execute(
        GuardarConexionArcaCommand(
            activa=activa, ambiente=AmbienteArca.PRODUCCION, cuit=cuit, usuario_id=ADMIN
        )
    )


def test_por_defecto_esta_apagada_y_se_carga_a_mano() -> None:
    conexion = ObtenerConexionArca(FakeRepo()).execute()
    assert conexion.activa is False
    assert conexion.lista_para_usar(HOY.date()) is False


def test_no_se_activa_sin_certificado() -> None:
    with pytest.raises(Conflicto, match="certificado"):
        _activar(FakeRepo())


def test_se_puede_guardar_apagada_sin_certificado() -> None:
    repo = FakeRepo()
    conexion = _activar(repo, activa=False)
    assert conexion.activa is False
    assert repo.conexion is not None
    assert repo.conexion.actualizado_por == ADMIN


def test_cargar_credenciales_toma_cuit_y_vencimiento_del_certificado() -> None:
    repo, boveda = FakeRepo(), FakeBoveda()
    _con_credenciales(repo, boveda)
    assert repo.conexion is not None
    assert repo.conexion.tiene_credenciales
    assert repo.conexion.cuit == Cuit(CUIT)
    assert repo.conexion.certificado_vence == date(2028, 1, 1)
    assert repo.conexion.activa is False  # cargar el certificado no la enciende


def test_archivo_vacio_o_enorme_se_rechaza() -> None:
    uc = CargarCredencialesArca(FakeRepo(), FakeBoveda(), FakeClock(HOY))
    with pytest.raises(ArchivoInvalido):
        uc.execute(CargarCredencialesCommand(certificado=b"", clave=b"k", usuario_id=ADMIN))
    with pytest.raises(ArchivoInvalido):
        uc.execute(
            CargarCredencialesCommand(certificado=b"x" * 70_000, clave=b"k", usuario_id=ADMIN)
        )


def test_activar_con_certificado_vigente() -> None:
    repo, boveda = FakeRepo(), FakeBoveda()
    _con_credenciales(repo, boveda)
    conexion = _activar(repo)
    assert conexion.activa
    assert conexion.lista_para_usar(HOY.date())


def test_no_se_activa_con_certificado_vencido() -> None:
    repo, boveda = FakeRepo(), FakeBoveda(vence=HOY.date() - timedelta(days=1))
    _con_credenciales(repo, boveda)
    with pytest.raises(Conflicto, match="venció"):
        _activar(repo)


def test_sin_cuit_no_se_activa() -> None:
    repo, boveda = FakeRepo(), FakeBoveda(cuit=None)
    _con_credenciales(repo, boveda)
    with pytest.raises(Conflicto, match="CUIT"):
        _activar(repo, cuit=None)


def test_resolver_padron_solo_si_esta_activa() -> None:
    repo, boveda, padron = FakeRepo(), FakeBoveda(), FakePadron()
    resolver = ResolverPadron(repo, boveda, _fabrica(padron), FakeClock(HOY))
    assert resolver.execute() is None  # sin configurar
    _con_credenciales(repo, boveda)
    assert resolver.execute() is None  # con certificado pero apagada
    _activar(repo)
    assert resolver.execute() is padron


def test_certificado_que_vence_despues_de_activar_apaga_las_sugerencias() -> None:
    repo, boveda, padron = FakeRepo(), FakeBoveda(vence=date(2026, 10, 10)), FakePadron()
    _con_credenciales(repo, boveda)
    _activar(repo)
    despues = FakeClock(datetime(2026, 10, 11, tzinfo=UTC))
    assert ResolverPadron(repo, boveda, _fabrica(padron), despues).execute() is None


def test_probar_consulta_el_propio_cuit_aunque_este_apagada() -> None:
    repo, boveda, padron = FakeRepo(), FakeBoveda(), FakePadron()
    _con_credenciales(repo, boveda)
    datos = ProbarConexionArca(repo, boveda, _fabrica(padron)).execute()
    assert datos is not None
    assert padron.consultados == [CUIT]


def test_probar_sin_certificado_avisa() -> None:
    with pytest.raises(Conflicto, match="certificado"):
        ProbarConexionArca(FakeRepo(), FakeBoveda(), _fabrica(FakePadron())).execute()

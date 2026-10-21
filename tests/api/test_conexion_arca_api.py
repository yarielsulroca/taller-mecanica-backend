from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from taller.adapters.inbound.api.app import create_app
from taller.adapters.inbound.api.deps import get_current_user
from taller.adapters.inbound.api.deps_auditoria import uc_registrar_auditoria
from taller.adapters.inbound.api.deps_padron import boveda_arca, fabrica_arca, repo_conexion_arca
from taller.adapters.outbound.padron.boveda_arca import ArchivoBovedaArca
from taller.domain.entities.conexion_arca import ConexionArca
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.enums import CondicionIva
from taller.domain.ports.padron import CredencialesArca, DatosPadron
from tests.unit.test_arca_adapter import _credenciales
from tests.unit.test_conexion_arca import FakeRepo

API = "/api/v1"


class FakeAuditoria:
    def __init__(self) -> None:
        self.acciones: list[str] = []

    def execute(self, usuario: Usuario, **kwargs: Any) -> None:
        self.acciones.append(kwargs["accion"])


class PadronFijo:
    def consultar(self, cuit: str) -> DatosPadron | None:
        return DatosPadron(
            cuit=cuit, fuente="arca", razon_social="TALLER SRL",
            cond_iva=CondicionIva.RESPONSABLE_INSCRIPTO, cond_iva_texto="IVA Responsable Inscripto",
        )


def _usuario(*roles: Rol) -> Usuario:
    return Usuario(id=uuid4(), nombre="x", email="x@x.com", password_hash="-",
                   roles=frozenset(roles))


@pytest.fixture
def entorno(tmp_path: Path) -> Iterator[dict[str, Any]]:
    app = create_app()
    estado: dict[str, Any] = {
        "usuario": _usuario(Rol.ADMIN), "repo": FakeRepo(), "audit": FakeAuditoria(),
    }

    def fabrica(c: ConexionArca, cred: CredencialesArca) -> PadronFijo:
        return PadronFijo()

    app.dependency_overrides[get_current_user] = lambda: estado["usuario"]
    app.dependency_overrides[repo_conexion_arca] = lambda: estado["repo"]
    app.dependency_overrides[boveda_arca] = lambda: ArchivoBovedaArca(tmp_path)
    app.dependency_overrides[fabrica_arca] = lambda: fabrica
    app.dependency_overrides[uc_registrar_auditoria] = lambda: estado["audit"]
    estado["client"] = TestClient(app)
    yield estado


def _subir(client: TestClient) -> Any:
    cred = _credenciales("20123456786")
    return client.post(
        f"{API}/configuracion-taller/arca/credenciales",
        files={
            "certificado": ("taller.crt", cred.certificado),
            "clave": ("taller.key", cred.clave),
        },
    )


def test_por_defecto_apagada_y_sin_boton(entorno: dict[str, Any]) -> None:
    c = entorno["client"]
    r = c.get(f"{API}/configuracion-taller/arca")
    assert r.status_code == 200
    assert r.json()["activa"] is False
    assert c.get(f"{API}/padron/estado").json() == {"disponible": False}
    assert c.get(f"{API}/padron/30712345678").json() is None  # carga manual


def test_solo_admin_configura(entorno: dict[str, Any]) -> None:
    entorno["usuario"] = _usuario(Rol.ADMINISTRACION)
    c = entorno["client"]
    assert c.get(f"{API}/configuracion-taller/arca").status_code == 403
    assert _subir(c).status_code == 403
    assert c.get(f"{API}/padron/estado").status_code == 200  # el estado lo ve cualquiera


def test_flujo_completo(entorno: dict[str, Any]) -> None:
    c = entorno["client"]
    r = c.put(f"{API}/configuracion-taller/arca", json={"activa": True, "ambiente": "produccion"})
    assert r.status_code == 409  # sin certificado no se activa

    r = _subir(c)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["tiene_credenciales"] is True
    assert cuerpo["cuit"] == "20123456786"
    assert "clave" not in cuerpo

    r = c.post(f"{API}/configuracion-taller/arca/probar")
    assert r.json()["ok"] is True
    assert r.json()["datos"]["razon_social"] == "TALLER SRL"

    r = c.put(f"{API}/configuracion-taller/arca",
              json={"activa": True, "ambiente": "produccion", "cuit": "20123456786"})
    assert r.status_code == 200
    assert r.json()["lista_para_usar"] is True
    assert c.get(f"{API}/padron/estado").json() == {"disponible": True}
    sugerencia = c.get(f"{API}/padron/30712345678").json()
    assert sugerencia["cond_iva"] == "responsable_inscripto"
    assert entorno["audit"].acciones == ["cargar_certificado", "probar", "activar"]


def test_clave_que_no_corresponde_da_422(entorno: dict[str, Any]) -> None:
    uno, otro = _credenciales(), _credenciales()
    r = entorno["client"].post(
        f"{API}/configuracion-taller/arca/credenciales",
        files={"certificado": ("a.crt", uno.certificado), "clave": ("b.key", otro.clave)},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "archivo_invalido"

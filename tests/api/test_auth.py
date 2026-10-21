from __future__ import annotations

from fastapi.testclient import TestClient

from taller.adapters.inbound.api.app import create_app


def test_health() -> None:
    client = TestClient(create_app())
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_login_sin_credenciales_validas_devuelve_error() -> None:
    client = TestClient(create_app())
    # Payload inválido (email mal formado) -> validación de esquema.
    respuesta = client.post("/api/v1/auth/login", json={"email": "no-es-email", "password": "x"})
    assert respuesta.status_code == 422


def test_me_sin_token_devuelve_401() -> None:
    client = TestClient(create_app())
    respuesta = client.get("/api/v1/auth/me")
    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "no_autenticado"

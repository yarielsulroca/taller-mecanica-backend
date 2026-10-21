import pytest
from pydantic import ValidationError

from taller.config import Settings


def test_prod_rechaza_secreto_de_ejemplo() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="prod",
            jwt_secret="cambiar-este-secreto-por-uno-de-32-bytes-minimo",
        )


def test_prod_rechaza_secreto_corto() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="prod", jwt_secret="corto")


def test_prod_acepta_secreto_propio() -> None:
    s = Settings(_env_file=None, environment="prod", jwt_secret="x" * 48)
    assert s.environment == "prod"


def test_dev_tolera_secreto_por_defecto() -> None:
    assert Settings(_env_file=None, environment="dev").jwt_secret


def test_mysql_arma_url_con_charset() -> None:
    s = Settings(_env_file=None, db_motor="mysql", db_usuario="u", db_password="p@ss")
    assert s.url_base_datos == "mysql+pymysql://u:p%40ss@localhost:3306/taller?charset=utf8mb4"


def test_frontend_url_se_agrega_a_cors() -> None:
    s = Settings(
        _env_file=None,
        frontend_url="https://app.ejemplo.com/",
        cors_origins=["http://localhost:3000"],
    )
    assert "https://app.ejemplo.com" in s.cors_origins
    assert "http://localhost:3000" in s.cors_origins

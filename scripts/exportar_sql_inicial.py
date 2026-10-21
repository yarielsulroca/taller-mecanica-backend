"""Genera el .sql inicial para importar en MariaDB/MySQL (phpMyAdmin o consola).

Incluye la estructura completa (al día con las migraciones), los catálogos de
los selects (rubros, tipos de pago, glosario), la versión de Alembic y un
usuario admin. No incluye datos de trabajo (OT, clientes, movimientos, etc.).

La contraseña del admin se genera al azar y se escribe en un archivo aparte
(no en el .sql ni en la consola). Cambiala después del primer ingreso.

Requisitos: una base MariaDB/MySQL local ya migrada (`alembic upgrade head`)
y con catálogos (`python -m scripts.seed_catalogos`), y `mysqldump`.

Uso (desde backend/):
    python -m scripts.exportar_sql_inicial --base taller --usuario root
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from taller.adapters.outbound.security.password_hasher import Argon2PasswordHasher

TABLAS_CON_DATOS = ("alembic_version", "glosario", "rubros", "tipos_pago")
_XAMPP = Path(r"C:\xampp\mysql\bin\mysqldump.exe")
_DEPLOY = Path(__file__).resolve().parents[2] / "deploy"


def _mysqldump(args: argparse.Namespace, *extra: str, tablas: tuple[str, ...] = ()) -> str:
    comando = [
        args.mysqldump,
        f"--host={args.host}",
        f"--port={args.puerto}",
        f"--user={args.usuario}",
        "--default-character-set=utf8mb4",
        "--skip-comments",
        "--skip-add-drop-table",
        "--skip-lock-tables",
        *extra,
        args.base,
        *tablas,
    ]
    resultado = subprocess.run(comando, capture_output=True, check=True)
    return resultado.stdout.decode("utf-8")


def _texto(valor: str) -> str:
    return "'" + valor.replace("\\", "\\\\").replace("'", "''") + "'"


def _insert_admin(email: str, nombre: str, password_hash: str) -> str:
    ahora = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
    valores = ", ".join(
        [
            _texto(uuid.uuid4().hex),
            _texto(nombre),
            _texto(email.lower()),
            _texto(password_hash),
            _texto(json.dumps(["admin"])),
            "1",
            _texto(ahora),
            _texto(ahora),
        ]
    )
    return (
        "INSERT INTO `usuarios` (`id`, `nombre`, `email`, `password_hash`, `roles`, "
        f"`activo`, `created_at`, `updated_at`) VALUES ({valores});\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el SQL inicial para MariaDB/MySQL")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=3306)
    parser.add_argument("--usuario", default="root")
    parser.add_argument("--base", default="taller")
    parser.add_argument(
        "--mysqldump", default=str(_XAMPP) if _XAMPP.exists() else shutil.which("mysqldump")
    )
    # Dominio real: la API rechaza los reservados (.local, .test, ...).
    parser.add_argument("--admin-email", default="admin@taller.com.ar")
    parser.add_argument("--admin-nombre", default="Administrador")
    parser.add_argument("--salida", type=Path, default=_DEPLOY / "taller_inicial_mariadb.sql")
    args = parser.parse_args()
    if not args.mysqldump:
        raise SystemExit("No se encontró mysqldump; indicalo con --mysqldump")

    estructura = _mysqldump(args, "--no-data")
    datos = _mysqldump(
        args, "--no-create-info", "--complete-insert", tablas=TABLAS_CON_DATOS
    )

    password = secrets.token_urlsafe(12)
    password_hash = Argon2PasswordHasher().hash(password)
    admin = _insert_admin(args.admin_email, args.admin_nombre, password_hash)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(
        "-- Taller Mecánico: estructura + catálogos + admin inicial (sin datos de trabajo).\n"
        "-- Importar en una base VACÍA con juego de caracteres utf8mb4.\n"
        f"-- Generado: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC\n\n"
        "SET NAMES utf8mb4;\n"
        "SET FOREIGN_KEY_CHECKS = 0;\n\n"
        f"{estructura}\n"
        "-- Catálogos de los selects y versión de las migraciones\n"
        f"{datos}\n"
        "-- Usuario admin inicial (la contraseña está en ADMIN_INICIAL.txt)\n"
        f"{admin}\n"
        "SET FOREIGN_KEY_CHECKS = 1;\n",
        encoding="utf-8",
    )

    credencial = args.salida.parent / "ADMIN_INICIAL.txt"
    credencial.write_text(
        "Usuario admin inicial del .sql\n"
        f"Email: {args.admin_email.lower()}\n"
        f"Contraseña: {password}\n\n"
        "Cambiala después del primer ingreso y borrá este archivo.\n",
        encoding="utf-8",
    )
    os.chmod(credencial, 0o600)
    print(f"SQL generado: {args.salida}")
    print(f"Credencial del admin en: {credencial} (no se muestra acá)")


if __name__ == "__main__":
    main()

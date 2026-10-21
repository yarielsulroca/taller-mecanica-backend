"""Crea el primer usuario admin si no existe.

Uso:
    python -m scripts.crear_admin --email admin@taller.local --password "secreto" --nombre Admin

Requiere que las migraciones estén aplicadas.
"""

from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.usuario_repository import SqlUsuarioRepository
from taller.container import build_container
from taller.domain.entities.usuario import Rol, Usuario


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea el usuario admin inicial")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--nombre", default="Administrador")
    args = parser.parse_args()

    container = build_container()
    with Session(container.engine) as session:
        repo = SqlUsuarioRepository(session)
        if repo.obtener_por_email(args.email.lower()) is not None:
            print(f"El usuario {args.email} ya existe.")
            return
        usuario = Usuario.crear(
            nombre=args.nombre,
            email=args.email,
            password_hash=container.hasher.hash(args.password),
            roles={Rol.ADMIN},
        )
        repo.guardar(usuario)
        session.commit()
        print(f"Usuario admin creado: {usuario.email}")


if __name__ == "__main__":
    main()

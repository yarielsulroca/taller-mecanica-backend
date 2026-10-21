"""Carga los catálogos iniciales: rubros y tipos de pago.

Idempotente: se puede correr las veces que haga falta; sólo agrega lo que falta
y no revive lo que el admin archivó. Después se editan desde Administración.

Uso (desde backend/, con las migraciones aplicadas):
    python -m scripts.seed_catalogos
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.maestros_repositories import (
    SqlRubroRepository,
    SqlTipoPagoRepository,
)
from taller.application.use_cases.catalogos import SembrarCatalogos, SembrarCatalogosCommand
from taller.container import build_container

# Regla de clasificación (01-logica-negocio §11.3): bien → rubro; ni bien ni
# servicio → rubro (costo / impuesto); labor o servicio → tipo de pago.
RUBROS: tuple[tuple[str, str], ...] = (
    ("Repuestos", "bien"),
    ("Lubricantes y fluidos", "bien"),
    ("Filtros", "bien"),
    ("Neumáticos", "bien"),
    ("Baterías", "bien"),
    ("Frenos", "bien"),
    ("Electricidad y electrónica", "bien"),
    ("Carrocería y pintura", "bien"),
    ("Insumos de taller", "bien"),
    ("Herramientas y equipamiento", "bien"),
    ("Librería y oficina", "bien"),
    ("Limpieza", "bien"),
    ("Comisiones bancarias", "costo"),
    ("Seguros", "costo"),
    ("Ajustes", "costo"),
    ("IVA", "impuesto"),
    ("Ingresos Brutos", "impuesto"),
    ("Tasas municipales", "impuesto"),
    ("Monotributo", "impuesto"),
    ("Cargas sociales", "impuesto"),
)

TIPOS_PAGO: tuple[str, ...] = (
    "Sueldo",
    "Jornal",
    "Comisión",
    "Adelanto de sueldo",
    "Honorarios profesionales",
    "Mano de obra tercerizada",
    "Tornería",
    "Rectificación",
    "Chapa y pintura tercerizada",
    "Grúa / auxilio",
    "Flete",
    "Alquiler",
    "Electricidad",
    "Gas",
    "Agua",
    "Internet y teléfono",
    "Software y suscripciones",
    "Mantenimiento del local",
    "Publicidad",
)


def main() -> None:
    container = build_container()
    with Session(container.engine) as session:
        uc = SembrarCatalogos(SqlRubroRepository(session), SqlTipoPagoRepository(session))
        resultado = uc.execute(SembrarCatalogosCommand(rubros=RUBROS, tipos_pago=TIPOS_PAGO))
        session.commit()
    print(f"Rubros agregados: {len(resultado.rubros_creados)}")
    for nombre in resultado.rubros_creados:
        print(f"  + {nombre}")
    print(f"Tipos de pago agregados: {len(resultado.tipos_pago_creados)}")
    for nombre in resultado.tipos_pago_creados:
        print(f"  + {nombre}")
    if not resultado.rubros_creados and not resultado.tipos_pago_creados:
        print("Nada para agregar: los catálogos ya estaban completos.")


if __name__ == "__main__":
    main()

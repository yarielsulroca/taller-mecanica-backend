"""Inventario rápido de endpoints por tag + huecos contra el doc 02."""
from __future__ import annotations

import httpx

s = httpx.get("http://127.0.0.1:8000/openapi.json", timeout=15).json()
print("rutas:", len(s["paths"]), "operaciones:", sum(len(m) for m in s["paths"].values()))

tags: dict[str, list[str]] = {}
for path, metodos in s["paths"].items():
    for metodo, detalle in metodos.items():
        for tag in detalle.get("tags", ["sin-tag"]):
            tags.setdefault(tag, []).append(f"{metodo.upper():6} {path}")

for tag, lista in sorted(tags.items()):
    print(f"\n[{tag}] ({len(lista)})")
    for item in sorted(lista):
        print("  ", item)

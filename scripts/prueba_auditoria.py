"""E2E del pack de auditoría contra la API viva:
1. login admin 2. una escritura (POST /texto/registrar) 3. leer /auditoria.
"""
from __future__ import annotations

import time

import httpx

BASE = "http://127.0.0.1:8000"

with httpx.Client(base_url=BASE, timeout=30) as http:
    login = {"email": "admin@taller.com.ar", "password": "cambiar123"}
    r = http.post("/api/v1/auth/login", json=login)
    print("login ->", r.status_code)
    h = {"Authorization": "Bearer " + (r.json().get("access_token") or "")}

    # Escritura inocua: registra un término en el glosario del asistente.
    w = http.post(
        "/api/v1/texto/registrar",
        headers=h,
        json={"terminos": ["cambio-de-bujes-test-auditoria"]},
    )
    print("POST /texto/registrar ->", w.status_code)

    time.sleep(1.5)  # el middleware graba después de responder

    logs = http.get("/api/v1/auditoria", headers=h).json()
    print(f"\n/auditoria ({len(logs)} registros):")
    for log in logs[:10]:
        print(
            f"  {str(log['fecha'])[:19]}  {log['usuario_nombre'][:14]:14} "
            f"{log['accion']:7} {log['entidad']:12} {str(log['detalle'])[:60]}"
        )
    if not logs:
        print("  (vacío — ¿el servidor no recargó el middleware?)")

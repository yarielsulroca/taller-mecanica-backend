"""Smoke de login + endpoints protegidos contra la API viva (timeout holgado, con tiempos)."""
from __future__ import annotations

import time

import httpx

BASE = "http://127.0.0.1:8000"

with httpx.Client(base_url=BASE, timeout=45) as http:
    login = {"email": "admin@taller.com.ar", "password": "cambiar123"}
    r = http.post("/api/v1/auth/login", json=login)
    print("login ->", r.status_code)
    tok = r.json().get("access_token") or r.json().get("token") or ""
    h = {"Authorization": "Bearer " + tok}

    rutas = (
        "/api/v1/configuracion-taller",
        "/api/v1/condiciones-iva",
        "/api/v1/finanzas/medios-de-pago",
        "/api/v1/padron/30712345678",
    )
    for ruta in rutas:
        t0 = time.perf_counter()
        try:
            rr = http.get(ruta, headers=h)
            dt = time.perf_counter() - t0
            json_ok = rr.headers.get("content-type", "").startswith("application/json")
            cuerpo = str(rr.json())[:150] if json_ok else "(html)"
            print(f"GET {ruta:36} -> {rr.status_code} {dt:.2f}s {cuerpo}")
        except Exception as e:  # noqa: BLE001
            print(f"GET {ruta:36} -> ERROR {type(e).__name__} en {time.perf_counter() - t0:.2f}s")

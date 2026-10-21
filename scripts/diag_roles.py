"""Diagnóstico RBAC del jefe de taller: ¿qué ve y qué puede hacer?"""
from __future__ import annotations

import httpx  # noqa: E402  (script de diagnóstico, se importa al final a propósito)

BASE = "http://127.0.0.1:8000"
JUEFE = {"email": "jefe@taller.com.ar", "password": "cambiar123"}  # fallback abajo


def probar(http: httpx.Client, email: str, password: str) -> None:
    print(f"\n===== {email} =====")
    r = http.post("/api/v1/auth/login", json={"email": email, "password": password})
    print("login ->", r.status_code)
    if r.status_code != 200:
        return
    tok = r.json().get("access_token") or r.json().get("token") or ""
    h = {"Authorization": "Bearer " + tok}

    me = http.get("/api/v1/auth/me", headers=h).json()
    print("usuario:", me.get("nombre"), "| roles:", me.get("roles") or me.get("rol"))

    # 1) Listar órdenes (poder leer)
    r1 = http.get("/api/v1/ordenes", headers=h)
    print("GET  /ordenes ->", r1.status_code)
    ordenes = (r1.json() if r1.status_code == 200 else [])
    if ordenes:
        ot_id = ordenes[0]["id"]
        # 2) Detalle completo con precios (lo que falla en la UI)
        r2 = http.get(f"/api/v1/ordenes/{ot_id}", headers=h)
        cuerpo2 = r2.json() if r2.status_code == 200 else r2.text[:120]
        print("GET  /ordenes/{id} ->", r2.status_code, "| claves:" )
        if r2.status_code == 200 and isinstance(cuerpo2, dict):
            print("   ", list(cuerpo2.keys())[:14])
        # 3) Asignar responsable de la primera operación
        items = r2.json().get("items", []) if r2.status_code == 200 else []
        if items:
            r3 = http.post(
                f"/api/v1/ordenes/{ot_id}/items/{items[0]['id']}/responsable",
                headers=h,
                json={"mecanico_id": items[0].get("mecanico_id") or ""},
            )
            print(
                "POST /ordenes/../responsable (asignar) ->",
                r3.status_code,
                "" if r3.status_code in (200, 201) else str(r3.json())[:110],
            )
        # 4) Ver la lista de trabajadores (necesaria para elegir mecánico)
        r4 = http.get("/api/v1/trabajadores", headers=h)
        print("GET  /trabajadores ->", r4.status_code)


with httpx.Client(base_url=BASE, timeout=15) as http:
    # El jefe real es "Mecanico Perez Perez" (perez@taller.com.ar, roles combinados).
    for correo in ("perez@taller.com.ar",):
        try:
            probar(http, correo, "cambiar123")
        except Exception as e:  # noqa: BLE001
            print("error:", type(e).__name__, e)

print("\n== usuarios existentes con esos roles (DB) ==")
import psycopg  # noqa: E402

conn = psycopg.connect("postgresql://taller:taller@localhost:5432/taller")
cur = conn.cursor()
cur.execute("select email, nombre, roles, activo from usuarios order by created_at")
for fila in cur.fetchall():
    print("  ", fila)
conn.close()

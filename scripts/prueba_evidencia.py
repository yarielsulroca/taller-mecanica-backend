"""Prueba live: GET archivo de evidencia + preview URL del panel."""
from __future__ import annotations

import httpx
import psycopg

conn = psycopg.connect("postgresql://taller:taller@localhost:5432/taller")
cur = conn.cursor()
cur.execute(
    "select ot_id, id, nombre_original, tipo from evidencias order by creada_en desc limit 3"
)
filas = cur.fetchall()
conn.close()
if not filas:
    print("sin evidencias")
    raise SystemExit

ot_id, ev_id, nombre, tipo = filas[0]
print("evidencia:", nombre, "| tipo:", tipo)

with httpx.Client(base_url="http://127.0.0.1:8000", timeout=20) as http:
    login = {"email": "admin@taller.com.ar", "password": "cambiar123"}
    r = http.post("/api/v1/auth/login", json=login)
    h = {"Authorization": "Bearer " + (r.json().get("access_token") or "")}
    a = http.get(f"/api/v1/ordenes/{ot_id}/evidencias/{ev_id}/archivo", headers=h)
    print("GET archivo ->", a.status_code, "| media:", a.headers.get("content-type"),
          "| bytes:", len(a.content))

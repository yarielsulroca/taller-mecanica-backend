"""Puntualiza el efectivo pendiente existente y verifica el dashboard en vivo."""
from __future__ import annotations

import httpx
import psycopg

conn = psycopg.connect("postgresql://taller:taller@localhost:5432/taller")
cur = conn.cursor()
cur.execute(
    "update movimientos set estado='comprobado'"
    " where medio='efectivo' and estado='pendiente' returning monto"
)
print("comprobado(s):", cur.fetchall())
conn.commit()
conn.close()

with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as http:
    login = {"email": "admin@taller.com.ar", "password": "cambiar123"}
    r = http.post("/api/v1/auth/login", json=login)
    h = {"Authorization": "Bearer " + (r.json().get("access_token") or "")}
    d = http.get("/api/v1/finanzas/dashboard", headers=h).json()
    print("dashboard:")
    for k, v in d.items():
        print(f"   {k:20} {v}")

"""Diagnóstico: dónde quedó el pago de 800000 y qué ve el dashboard."""
from __future__ import annotations

import httpx
import psycopg

conn = psycopg.connect("postgresql://taller:taller@localhost:5432/taller")
cur = conn.cursor()

print("== MOVIMIENTOS (todos los estados) ==")
cur.execute(
    """
    select m.fecha, m.signo, m.naturaleza, m.monto, m.medio, m.estado,
           coalesce(t.nombre, '—') as trabajador
    from movimientos m
    left join trabajadores t on t.id = m.trabajador_id
    order by m.created_at desc limit 20
    """
)
for fila in cur.fetchall():
    print("  ", fila)

print("\n== ADELANTOS ==")
cur.execute("select fecha, monto, estado, motivo from adelantos order by fecha desc limit 5")
for fila in cur.fetchall():
    print("  ", fila)

print("\n== LIQUIDACIONES ==")
cur.execute(
    "select periodo_desde, periodo_hasta, monto_bruto, adelantos_descontados, estado"
    " from liquidaciones order by periodo_hasta desc limit 5"
)
for fila in cur.fetchall():
    print("  ", fila)

print("\n== TRABAJADORES ==")
cur.execute("select nombre, rol, tipo_remuneracion, costo_hora, monto_periodo from trabajadores")
for fila in cur.fetchall():
    print("  ", fila)

conn.close()

print("\n== DASHBOARD (via API viva) ==")
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=20) as http:
    r = http.post(
        "/api/v1/auth/login", json={"email": "admin@taller.com.ar", "password": "cambiar123"}
    )
    h = {"Authorization": "Bearer " + (r.json().get("access_token") or "")}
    d = http.get("/api/v1/finanzas/dashboard", headers=h).json()
    for k, v in d.items():
        print(f"   {k:20} {v}")

    print("\n== ADELANTOS via API ==")
    print("   ", http.get("/api/v1/pagos/adelantos", headers=h).json())

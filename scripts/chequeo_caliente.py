"""Chequeo en caliente: tablas/columnas de P1/P2 + smoke HTTP contra la API viva."""
from __future__ import annotations

import httpx
import psycopg

BASE = "http://127.0.0.1:8000/api/v1"

conn = psycopg.connect("postgresql://taller:taller@localhost:5432/taller")
cur = conn.cursor()
cur.execute(
    """
    select
      (select to_regclass('public.configuracion_taller') is not null) as t_config,
      (select to_regclass('public.puntos_venta_taller') is not null) as t_pdv,
      (select to_regclass('public.comprobante_ordenes') is not null) as t_cotp,
      (select column_name from information_schema.columns
        where table_name='compras' and column_name='comprobante_id') as c_comp_id,
      (select column_name from information_schema.columns
        where table_name='proveedores' and column_name='cond_iva') as c_prov_iva,
      (select column_name from information_schema.columns
        where table_name='ordenes_trabajo' and column_name='presupuesto_vigente_hasta') as c_vig,
      (select column_name from information_schema.columns
        where table_name='movimientos' and column_name='retenciones') as c_ret,
      (select column_name from information_schema.columns
        where table_name='ot_items' and column_name='costo_unitario') as c_costo
    """
)
etiquetas = ("configuracion_taller", "puntos_venta", "comprobante_ordenes",
             "compras.comprobante_id", "proveedores.cond_iva",
             "ot.vigencia", "movimientos.retenciones", "ot_items.costo_unitario")
for etiqueta, valor in zip(etiquetas, cur.fetchone(), strict=True):
    estado = "OK" if valor else "FALTA"
    print(f"  {etiqueta:24} {estado}")

cur.execute("select count(*) from information_schema.tables where table_schema='public'")
print("\ntablas public:", cur.fetchone()[0])
conn.close()

print("\n--- HTTP (API viva en :8000) ---")
with httpx.Client(base_url=BASE, timeout=10) as http:
    ping = http.get("/health")
    print("GET  /health                  ->", ping.status_code)
    conf = http.get("/configuracion-taller")
    print("GET  /configuracion-taller    ->", conf.status_code, "(401 esperado sin token)")
    tipo = http.get("/configuracion-taller/tipo-comprobante")
    print("GET  /tipo-comprobante        ->", tipo.status_code)
    med = http.get("/finanzas/medios-de-pago")
    print("GET  /finanzas/medios-de-pago ->", med.status_code)
    opc = http.get("/condiciones-iva")
    print("GET  /condiciones-iva         ->", opc.status_code)

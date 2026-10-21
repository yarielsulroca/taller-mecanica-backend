# Backend — Taller Mecánico

API en **FastAPI** con arquitectura **hexagonal**. Ver [docs/02-logica-aplicacion.md](../docs/02-logica-aplicacion.md).

## Requisitos

- Python 3.11+
- PostgreSQL 16 (o Docker)
- (Opcional) Tesseract para OCR — Fase 5

## Puesta en marcha

```powershell
# 1. Base de datos
docker compose up -d db          # desde la raíz del repo

# 2. Entorno Python
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

# 3. Configuración
Copy-Item .env.example .env      # ajustar si hace falta

# 4. Migraciones
alembic upgrade head

# 5. Primer admin
python -m scripts.crear_admin --email admin@taller.local --password "cambiar123" --nombre Admin

# 6. Servidor
uvicorn taller.main:app --reload --port 8000
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## Frontend en otro subdominio

Si la interfaz Next.js está en otro host (por ejemplo `https://app.tudominio.com`), en `.env`:

```env
TALLER_FRONTEND_URL=https://app.tudominio.com
```

En el frontend, `API_URL=https://api.tudominio.com`. Detalle: [deploy/hosting/env-ejemplo-subdominios.md](../deploy/hosting/env-ejemplo-subdominios.md).

## Tests

```powershell
pytest            # dominio, casos de uso (fakes), adaptadores y API
```

## Estructura

```
src/taller/
  domain/        entidades, value objects, excepciones, ports/
  application/   use_cases/, dto/
  adapters/inbound/api/     routers, auth, rbac, error handlers
  adapters/outbound/        postgres/, security/, clock
  container.py   composition root
  main.py        entrada ASGI
```

Regla de dependencia: `adapters → application → domain`.

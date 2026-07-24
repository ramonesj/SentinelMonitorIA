# SentinelMonitorIA: runbook local y preproducción

Este runbook cubre las operaciones que pueden ejecutarse sin AWS. No contiene secretos reales y no sustituye un procedimiento de despliegue cloud.

## Prerrequisitos

- Docker Desktop iniciado y `docker compose` disponible.
- PowerShell desde la raíz del repositorio.
- Puertos libres: `3000`, `5432`, `6379`, `8000`, `8080` y `8081` para el stack completo.

## Arranque de desarrollo

```powershell
.\scripts\check-docker.ps1
.\scripts\start-local.ps1 -Build
Invoke-RestMethod http://localhost:8000/health
```

Para el frontend manual:

```powershell
Push-Location frontend
npm ci
npm run dev
Pop-Location
```

Para levantar backend y frontend desde Docker:

```powershell
.\scripts\start-local.ps1 -Build -Frontend
.\scripts\test-local.ps1 -RequireFrontend
```

No ejecutes ambos modos de frontend al mismo tiempo: Vite manual y `sentinel-frontend` usan el puerto `3000`.

El frontend Docker usa una imagen autocontenida: no monta `frontend/` ni persiste un volumen de `node_modules`. Después de cambiar código o dependencias, repetir `-Build -Frontend`. El contexto Docker excluye `.env`, `.env.*`, logs y cachés; las imágenes se ejecutan como usuarios no root.

Para validar el frontend Docker sin ocupar el puerto `3000` del host:

```powershell
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml config --quiet
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml build frontend
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml run -T --rm --no-deps frontend npm run build
```

## Validación local-production

No reutilizar el `.env` de desarrollo. Generar un archivo temporal a partir de `backend/.env.local-production.example`, reemplazar todos los placeholders y no versionarlo.

```powershell
Copy-Item backend\.env.local-production.example backend\.env.local-production
# Editar backend\.env.local-production y sustituir secretos

docker compose --env-file backend\.env.local-production -f backend\docker-compose.local-production.yml config --quiet
docker compose --env-file backend\.env.local-production -f backend\docker-compose.local-production.yml up -d --build

docker compose --env-file backend\.env.local-production -f backend\docker-compose.local-production.yml ps
docker exec sentinel-backend-local-production alembic current
Invoke-RestMethod http://localhost:8000/health
```

El resultado esperado es `20260723_0003 (head)` y `status: healthy`, con PostgreSQL y Redis saludables. Para detenerlo sin eliminar datos:

```powershell
docker compose --env-file backend\.env.local-production -f backend\docker-compose.local-production.yml down
```

No usar `down -v` ni `start-local.ps1 -Clean` durante una validación normal.

## Pruebas

Smoke check read-only del stack:

```powershell
.\scripts\test-local.ps1 -RequireFrontend
```

Con el stack normal levantado:

```powershell
docker exec sentinel-backend pytest -q
docker exec sentinel-backend pytest -q tests/unit/test_security_boundaries.py
git diff --check
```

La suite backend validada contiene 19 pruebas correctas y una omitida cuando el stack usa `QUEUE_PROVIDER=mock`; la prueba omitida requiere Redis Streams y el worker persistente. Los warnings actuales son deprecaciones no bloqueantes de Pydantic y `datetime.utcnow`.

Frontend:

```powershell
Push-Location frontend
npm ci
npm test
npm run build
npm audit --audit-level=high
Pop-Location
```

Los resultados de la validación más reciente, los comandos completos y las limitaciones conocidas están en [`local-validation-report.md`](local-validation-report.md).

## Diagnóstico

```powershell
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml ps
docker compose -f backend\docker-compose.yml logs --tail 200 backend frontend postgres redis
.\scripts\test-local.ps1
Invoke-RestMethod http://localhost:8000/health
```

Si el puerto `8000` está ocupado, detener primero el perfil que lo utiliza. Si una prueba devuelve `429` inesperadamente, comprobar que las claves `rate_limit:*` correspondan a una prueba anterior y no borrar la base Redis completa; el fixture de integración limpia únicamente esas claves.

## Migraciones y datos

```powershell
docker exec sentinel-backend alembic upgrade head
docker exec sentinel-backend alembic current
docker exec sentinel-postgres psql -U sentinel -d sentinelmonitoria -tAc "SELECT version_num FROM alembic_version;"
```

`docker compose down` conserva volúmenes. Los backups y la restauración real de PostgreSQL deben probarse antes de producción cloud.

## Seguridad operativa

- No subir `.env`, `.env.local-production` ni tokens.
- Mantener `.dockerignore` raíz y `backend/.dockerignore` para evitar copiar secretos locales a imágenes.
- Rotar `SECRET_KEY`, `JWT_SECRET_KEY`, contraseñas y API keys antes de un entorno compartido.
- Mantener Swagger desactivado fuera de desarrollo.
- Usar HTTPS fuera de localhost.
- No usar `down -v`, `-Clean` ni endpoints de reset como limpieza rutinaria: eliminan datos locales.
- Revisar `git status --short` y `git diff --check` antes de crear commits.

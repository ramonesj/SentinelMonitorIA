# SentinelMonitorIA Backend

Servicio FastAPI para autenticación, health checks, métricas e ingestión local de telemetry. La guía principal del proyecto está en [../README.md](../README.md); este archivo se concentra en el backend.

## Estado

Implementado para desarrollo local:

- FastAPI con Python 3.12.
- PostgreSQL async mediante SQLAlchemy 2.
- Redis async para health y servicios auxiliares.
- JWT access/refresh persistidos por `jti`, revocables y con refresh token de un solo uso.
- API keys persistidas con digest SHA-256, scopes, rotación explícita y revocación.
- Rate limiter, cola mock predeterminada y Redis Streams local opcional.
- Worker persistente de telemetry con consumer group, ACK, reintentos y dead-letter.
- Health checks y métricas Prometheus.
- Docker Compose de desarrollo con hot reload, override Redis/worker y frontend opcional autocontenido en Docker.

Pendiente:

- SQS/S3/OpenSearch reales.
- Integración E2E completa del agente Vector.

## Arquitectura

```text
Cliente web / agente
        │ HTTP + Bearer
        ▼
FastAPI /api/v1
   ├── auth       usuarios, JWT y API keys
   ├── health     dependencias y recursos
   └── telemetry  ingesta y estadísticas
        │
   ┌────┴─────┐
   ▼          ▼
PostgreSQL  Redis
        │
        ▼
Queue provider: `mock` (default) o Redis Streams + worker persistente (local)
```

## Inicio recomendado con Docker

Desde la raíz del repositorio:

```powershell
.\scripts\check-docker.ps1
.\scripts\start-local.ps1 -Build
```

Para incluir el frontend dentro del mismo Compose:

```powershell
.\scripts\start-local.ps1 -Build -Frontend
```

O directamente desde la raíz:

```powershell
docker compose -f backend\docker-compose.yml up -d --build
```

Comprobar:

```powershell
docker compose -f backend\docker-compose.yml ps
Invoke-RestMethod http://localhost:8000/health
```

### Frontend Docker opcional

El Compose principal no obliga a ejecutar Node. Para un arranque integrado y reproducible, usa el override:

```powershell
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml config --quiet
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml up -d --build
Invoke-WebRequest http://localhost:3000/ -UseBasicParsing
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml down
```

El servicio usa la imagen construida, que incluye el código y las dependencias fijadas por `frontend/package-lock.json`, y define `VITE_API_BASE_URL=http://localhost:8000`. Después de cambiar el frontend o sus dependencias, reconstruye con `--build`; el flujo manual conserva el hot reload. Detén cualquier Vite manual antes de levantarlo porque ambos perfiles usan el puerto `3000`.

### Redis Streams y worker persistente local

El Compose principal conserva `QUEUE_PROVIDER=mock` como comportamiento predeterminado. Para activar la cola durable local sin borrar PostgreSQL, Redis ni logs existentes, usa el override:

```powershell
docker compose -f backend\docker-compose.yml -f backend\docker-compose.redis-worker.yml config --quiet
docker compose -f backend\docker-compose.yml -f backend\docker-compose.redis-worker.yml up -d --build backend worker
docker compose -f backend\docker-compose.yml -f backend\docker-compose.redis-worker.yml ps
```

El override cambia únicamente el backend y añade `sentinel-worker` con `QUEUE_PROVIDER=redis`. El productor publica en `sentinel:stream:<queue>`; el worker usa el grupo `sentinel-telemetry-workers`, recupera pendientes con `XAUTOCLAIM`, confirma con `XACK` después del commit de PostgreSQL y conserva los mensajes agotados en `sentinel:stream:dead_letter`. No uses `down -v`: `docker compose down` conserva los volúmenes.

Comprobaciones del flujo:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/health
docker exec sentinel-redis redis-cli XPENDING sentinel:stream:telemetry sentinel-telemetry-workers
docker exec sentinel-postgres psql -U sentinel -d sentinelmonitoria -c "SELECT status, count(*) FROM telemetrybatch GROUP BY status;"
```

El worker reconcilia al arrancar batches `processing` o `retrying` cuyo `updated_at` supera `TELEMETRY_STALE_BATCH_SECONDS` y los marca `failed` con motivo auditable; no borra el batch ni sus métricas, logs o eventos. La idempotencia usa el estado `processed` y bloqueo de fila, por lo que una redelivery no duplica hijos.

Para inspeccionar y reprocesar la DLQ se requiere un access JWT:

```powershell
$headers = @{ Authorization = "Bearer ACCESS_JWT" }
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/telemetry/dead-letter" -Headers $headers
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/telemetry/dead-letter/STREAM_ID/replay" -Method Post -Headers $headers
```

El replay conserva la entrada original y sólo permite reencolarla una vez mediante una marca Redis. El proveedor `mock` devuelve conflicto para estas operaciones porque no tiene una DLQ durable.

Logs:

```powershell
docker compose -f backend\docker-compose.yml logs -f backend
```

Detener sin borrar datos:

```powershell
docker compose -f backend\docker-compose.yml down
```

El backend escucha en `http://localhost:8000`. Swagger está disponible en `http://localhost:8000/api/v1/docs` cuando `DEBUG=true`.

## Ejecución directa fuera de Docker

Requiere Python 3.12, PostgreSQL y Redis accesibles desde Windows.

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

En `backend/.env` usar `POSTGRES_HOST=localhost` y `REDIS_HOST=localhost`. En Compose, la aplicación recibe `POSTGRES_HOST=postgres` y `REDIS_HOST=redis`.

## Configuración efectiva

Las variables principales son:

```text
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=debug
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
API_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
JWT_SECRET_KEY=development-jwt-secret-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sentinelmonitoria
POSTGRES_USER=sentinel
POSTGRES_PASSWORD=sentinel123
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_STREAM_PREFIX=sentinel:stream
REDIS_STREAM_MAX_LENGTH=10000
REDIS_STREAM_CONSUMER_GROUP=sentinel-telemetry-workers
TELEMETRY_STALE_BATCH_SECONDS=3600
REDIS_DEAD_LETTER_REPLAY_KEY=sentinel:stream:dead_letter:replayed
QUEUE_PROVIDER=mock
MOCK_QUEUE_MAX_SIZE=10000
```

El nombre usado por `settings.py` es `ENVIRONMENT`; `APP_ENVIRONMENT` no configura ese campo. `API_CORS_ORIGINS` acepta una lista separada por comas o JSON.

Después de cambiar `requirements.txt`, reconstruir la imagen:

```powershell
docker compose -f backend\docker-compose.yml up -d --build backend
```

La compatibilidad local de password hashing está fijada en `passlib==1.7.4` y `bcrypt==4.0.1`.

## Migraciones y perfil local-production

El esquema se versiona con Alembic. Las revisiones son aditivas: el baseline completa tablas ausentes y la revisión de seguridad añade `jwtsession` y metadata de API keys sin borrar filas existentes.

```powershell
Set-Location backend
docker exec sentinel-backend alembic upgrade head
# Comprobar la revisión aplicada
docker exec sentinel-postgres psql -U sentinel -d sentinelmonitoria -tAc "SELECT version_num FROM alembic_version;"
```

Para el perfil seguro local, copiar `backend/.env.local-production.example`, reemplazar los placeholders y ejecutar desde la raíz:

```powershell
Copy-Item backend\.env.local-production.example backend\.env.local-production
docker compose --env-file backend\.env.local-production -f backend\docker-compose.local-production.yml config --quiet
docker compose --env-file backend\.env.local-production -f backend\docker-compose.local-production.yml up -d --build
```

El perfil usa secretos obligatorios, Redis autenticado, `DEBUG=false`, `API_RELOAD=false`, sin herramientas Adminer/Redis Commander y sin montar el código fuente. Usa volúmenes separados, por lo que no modifica los datos del Compose de desarrollo.


### Rutas raíz

- `GET /` información de aplicación.
- `GET /health` health resumido.
- `GET /metrics` métricas Prometheus.
- `GET /dev/stats` estadísticas de desarrollo.
- `POST /dev/reset` restablece tablas, Redis y colas; destructivo.
- `GET /dev/test-auth` devuelve un token de prueba; solo desarrollo.

### Auth

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/change-password`
- `POST /api/v1/auth/api-keys`
- `GET /api/v1/auth/api-keys`
- `POST /api/v1/auth/api-keys/{token_id}/rotate`
- `DELETE /api/v1/auth/api-keys/{token_id}`

Las API keys se crean con `organization_id`, se muestran una sola vez en la respuesta y quedan asociadas al usuario y organización. La lista nunca devuelve los valores completos. Las nuevas keys se guardan en PostgreSQL como digest SHA-256; las filas legacy que aún contienen el valor usable se migran automáticamente durante el arranque local y el validador conserva una migración de respaldo al primer uso válido. La revocación marca la key como inactiva.

Las API keys aceptan `telemetry:write` y `telemetry:read`; la primera se asigna por defecto y es necesaria para ingesta. La rotación conserva metadata salvo overrides, devuelve la nueva key una sola vez y revoca la anterior inmediatamente.

### Health

- `GET /api/v1/health`
- `GET /api/v1/health/liveness`
- `GET /api/v1/health/readiness`
- `GET /api/v1/health/detailed`
- `GET /api/v1/health/history`
- `GET /api/v1/health/dev/simulate-failure`
- `POST /api/v1/health/dev/reset-health`

### Telemetry

- `POST /api/v1/telemetry`: recibe batches con API key y responde `202`.
- `GET /api/v1/telemetry/health`.
- `GET /api/v1/telemetry/stats`.
- `GET /api/v1/telemetry/queues`.
- `GET /api/v1/telemetry/dead-letter`: inspección autenticada de fallos retenidos.
- `POST /api/v1/telemetry/dead-letter/{stream_id}/replay`: reencolado idempotente de una entrada DLQ; conserva el registro original.
- `POST /api/v1/telemetry/test`: validación simulada en desarrollo.
- `POST /api/v1/telemetry/dev/reset-queues`.
- `POST /api/v1/telemetry/dev/simulate-load`.

La ingesta normal valida la API key mediante `AuthenticationService.validate_api_token`: firma JWT, tipo `api_key`, existencia en PostgreSQL, `is_active`, expiración, usuario y organización. La key debe estar asociada a una organización.

## Ejemplo de ingesta

```powershell
$headers = @{
  Authorization = "Bearer API_KEY_GENERADA"
  "Content-Type" = "application/json"
}
$body = @{
  metadata = @{
    agent_id = "agent-local-001"
    hostname = "localhost"
    agent_version = "1.0.0"
    platform = "windows"
    architecture = "x64"
    tags = @{ environment = "local" }
  }
  metrics = @(
    @{ name = "system.cpu.usage"; value = 42.5; type = "gauge"; labels = @{} }
  )
  logs = @()
  events = @()
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/telemetry" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

El batch debe tener `metadata` y al menos una métrica, log o evento. El máximo total es 10.000 items.

## Ciclo de vida

En desarrollo, `src.main` realiza al iniciar:

1. Inicializa el pool de PostgreSQL.
2. Inicializa Redis.
3. Inicia el servicio telemetry.
4. Crea tablas sólo si el entorno es `local` o `development`.
5. Migra API keys legacy a digest cuando corresponde.
6. Ejecuta health checks iniciales.

En `local-production`, el contenedor ejecuta `alembic upgrade head` antes de Uvicorn y no depende de `Base.metadata.create_all`.

Al apagar, detiene telemetry y cierra Redis y PostgreSQL.

## Estructura

```text
backend/
├── src/main.py
├── src/api/v1/auth.py
├── src/api/v1/health.py
├── src/api/v1/telemetry.py
├── src/config/settings.py
├── src/database/database.py
├── src/database/redis.py
├── src/middleware/auth.py
├── src/models/user.py
├── src/models/organization.py
├── src/schemas/auth.py
├── src/schemas/telemetry.py
├── src/services/auth.py
├── src/services/rate_limiter.py
├── src/services/telemetry.py
├── alembic.ini
├── alembic/versions/          # Baseline y migraciones aditivas
├── docker-compose.yml
├── docker-compose.local-production.yml
├── requirements.txt
└── tests/
    ├── integration/test_auth_telemetry.py
    └── pytest.ini
```

## Validación

```powershell
Invoke-RestMethod http://localhost:8000/
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/health/readiness
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/health
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/stats
Invoke-WebRequest http://localhost:8000/metrics -UseBasicParsing
```

### Pruebas automatizadas

Con el stack local levantado, ejecutar desde la raíz:

```powershell
docker exec sentinel-backend pytest -q
```

La suite usa `pytest`, `pytest-asyncio` y `httpx`. Además de auth/API keys, incluye pruebas unitarias del contrato `QueueMessage`, serialización, `XADD`/estadísticas, consumer group/ACK y reintentos/dead-letter, más una integración que verifica que el worker Redis persiste un batch completo en `metric`, `logentry` y `event`. La integración Redis se omite cuando `QUEUE_PROVIDER` no es `redis`.

Las pruebas crean usuarios y organizaciones con identificadores únicos. No borran los volúmenes locales.

Para la validación completa se confirmó creación de una API key con organización, listado sin secreto, ingesta real con respuesta `202`, revocación con `200` y rechazo posterior con `401`. También se corrigieron la comparación entre fechas con y sin zona horaria, la serialización JSON de errores de telemetry y el echo SQL que podía imprimir parámetros sensibles.

### Correcciones finales de estabilidad y seguridad

- `GET /health` usa `jsonable_encoder` al construir el `JSONResponse`, evitando errores cuando la respuesta contiene fechas `datetime`.
- `TelemetryService` usa `jsonable_encoder` para calcular el tamaño del batch y para preparar `batch_data` antes de enviarlo a la cola mock. Esto evita `Object of type datetime is not JSON serializable` durante la ingesta.
- El middleware de autenticación ya no registra fragmentos del token Bearer cuando ocurre un error. Los logs conservan endpoint, IP y mensaje del error, pero no imprimen JWTs ni API keys.
- `echo=False` en la conexión SQL evita que SQLAlchemy imprima consultas con parámetros sensibles.

Después de modificar estos componentes, el contenedor debe reconstruirse y recrearse sin eliminar volúmenes:

```powershell
docker compose -f backend\docker-compose.yml build backend
docker compose -f backend\docker-compose.yml up -d --force-recreate backend
```

La comprobación final esperada es:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/health
docker compose -f backend\\docker-compose.yml ps
```

Los dos endpoints deben indicar `healthy` y el servicio `backend` debe aparecer como `healthy`. Un lote enviado con una API key activa debe devolver `202`; la misma key después de revocarse debe devolver `401`. En logs recientes no debe aparecer ningún patrón JWT de tres segmentos ni errores fatales.

Estas medidas están validadas para desarrollo local. Para producción todavía se requiere almacenar API keys mediante hash o cifrado, usar secretos externos, desactivar `DEBUG`/`--reload` y habilitar HTTPS.

## Límites y seguridad

- El logout y el cambio de contraseña revocan sesiones JWT persistidas; el refresh anterior no puede reutilizarse.
- Las API keys nuevas se guardan como digest SHA-256, tienen scopes y soportan rotación explícita; las legacy conservan compatibilidad y se migran progresivamente.
- `local-production` requiere secretos fuertes, Redis con password y migraciones Alembic; sigue siendo local y usa la cola mock.
- El Compose development mantiene Redis sin contraseña, herramientas de administración y secretos de ejemplo sólo para localhost.

## Licencia

Apache 2.0. Ver [../LICENSE](../LICENSE).

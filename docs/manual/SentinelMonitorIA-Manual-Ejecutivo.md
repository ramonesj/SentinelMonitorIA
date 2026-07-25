# SentinelMonitorIA
## Manual ejecutivo de instalación, uso y operación local

**Edición:** 1.0<br>
**Plataforma objetivo:** Windows 10/11 + Docker Desktop + PowerShell<br>
**Estado:** entorno local validado; AWS fuera de alcance en esta edición

> Este manual está pensado para que un operador o desarrollador pueda levantar, utilizar, comprobar y detener SentinelMonitorIA sin asistencia adicional. Los comandos están escritos para ejecutarse desde la raíz del repositorio.

## 1. Qué es SentinelMonitorIA

SentinelMonitorIA es una plataforma local de observabilidad y AIOps en evolución. El recorrido funcional validado es:

```text
Usuario → organización → sesión JWT → API key → agente → telemetry → PostgreSQL + cola mock/Redis Streams
```

El sistema permite:

- Registrar usuarios y organizaciones.
- Iniciar sesión y renovar sesiones JWT.
- Crear, listar, rotar y revocar API keys con scopes.
- Ingerir métricas, logs y eventos mediante la API.
- Consultar salud, métricas Prometheus y estadísticas de telemetry.
- Ejecutar procesamiento local con cola mock o Redis Streams + worker.
- Operar el frontend React/Vite manualmente o integrado en Docker.

AWS/SQS/S3/OpenSearch, ECS y el despliegue cloud son fases futuras. La carpeta `infra/cloudformation/` contiene diseño offline y no crea recursos.

## 2. Arquitectura local

```text
┌──────────────────────────────┐
│ React + Vite                 │  http://localhost:3000
│ Login, dashboard, Connections│
└──────────────┬───────────────┘
               │ HTTP + CORS + Bearer
               ▼
┌──────────────────────────────┐
│ FastAPI                      │  http://localhost:8000
│ Auth · Health · Telemetry    │
└──────────┬───────────┬───────┘
           │           │
           ▼           ▼
   PostgreSQL        Redis
   localhost:5432    localhost:6379
           │
           ▼
  mock queue o Redis Streams + worker
```

El Compose principal conserva `QUEUE_PROVIDER=mock`. El override `backend/docker-compose.redis-worker.yml` activa Redis Streams y el worker persistente sin borrar datos del stack base.

## 3. Requisitos

- Windows 10 u 11.
- Docker Desktop iniciado y Docker Compose v2 (`docker compose`).
- PowerShell.
- Node.js y npm para el frontend manual; la validación usó Node.js 24.14.1, npm 11.11.0 y Vite 8.1.5.
- Git opcional.
- Puertos libres: `3000`, `5432`, `6379`, `8000`, `8080` y `8081`.

El flujo recomendado ejecuta el backend dentro de Docker; no es necesario instalar Python en Windows.

## 4. Obtener y preparar el proyecto

Desde PowerShell:

```powershell
git clone https://github.com/ramonesj/SentinelMonitorIA.git
Set-Location SentinelMonitorIA
./scripts/check-docker.ps1
```

Si Docker no está en el PATH:

```powershell
$env:Path = "$env:LOCALAPPDATA/Programs/DockerDesktop/resources/bin;$env:Path"
docker --version
docker compose version
docker info
```

No copies secretos reales al repositorio. Los archivos `.env` locales están ignorados y los contextos Docker excluyen `.env`, `.env.*`, logs y cachés.

## 5. Arranque rápido recomendado

### 5.1 Levantar backend, base de datos y Redis

Primera ejecución o después de cambiar dependencias:

```powershell
./scripts/start-local.ps1 -Build
```

Ejecuciones posteriores:

```powershell
./scripts/start-local.ps1
```

Comprobar el stack:

```powershell
docker compose -f backend/docker-compose.yml ps
Invoke-RestMethod http://localhost:8000/health
```

### 5.2 Levantar también el frontend en Docker

El modo integrado usa una imagen Node autocontenida. No monta el código ni un volumen persistente de `node_modules`; después de modificar el frontend se debe reconstruir.

```powershell
# Detener antes cualquier Vite manual que ocupe el puerto 3000
./scripts/start-local.ps1 -Build -Frontend
./scripts/test-local.ps1 -RequireFrontend
```

Abrir:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/api/v1/docs`

### 5.3 Alternativa: frontend manual

El modo manual es el más cómodo para desarrollo con hot reload:

```powershell
Push-Location frontend
npm ci
npm run dev
Pop-Location
```

Abrir `http://localhost:3000`. No ejecutes al mismo tiempo el frontend manual y `sentinel-frontend` Docker.

## 6. Servicios y puertos

| Servicio | Dirección | Uso |
|---|---|---|
| Frontend React/Vite | `http://localhost:3000` | Login, dashboard y Connections |
| Backend FastAPI | `http://localhost:8000` | API principal |
| Swagger | `http://localhost:8000/api/v1/docs` | Documentación interactiva en desarrollo |
| OpenAPI | `http://localhost:8000/api/v1/openapi.json` | Contrato JSON |
| Health | `http://localhost:8000/health` | Estado resumido |
| Liveness | `http://localhost:8000/api/v1/health/liveness` | Proceso disponible |
| Readiness | `http://localhost:8000/api/v1/health/readiness` | Dependencias listas |
| Metrics | `http://localhost:8000/metrics` | Prometheus |
| Telemetry health | `http://localhost:8000/api/v1/telemetry/health` | Servicio de telemetry |
| PostgreSQL | `localhost:5432` | Persistencia |
| Redis | `localhost:6379` | Cache, rate limiting y colas |
| Adminer | `http://localhost:8080` | Administración PostgreSQL |
| Redis Commander | `http://localhost:8081` | Administración Redis |

Credenciales PostgreSQL del Compose de desarrollo, únicamente para localhost:

| Campo | Valor |
|---|---|
| Servidor desde Adminer | `postgres` |
| Servidor desde Windows | `localhost` |
| Usuario | `sentinel` |
| Contraseña | `sentinel123` |
| Base de datos | `sentinelmonitoria` |

## 7. Primer uso del dashboard

1. Abrir `http://localhost:3000`.
2. Elegir **Create account**.
3. Registrar nombre, usuario, email, contraseña y organización.
4. Iniciar sesión.
5. Confirmar que el dashboard muestre salud de PostgreSQL, Redis y telemetry.
6. Entrar en **Connections**.
7. Crear una API key con una organización y el scope `telemetry:write`.
8. Copiar el secreto inmediatamente: se muestra completo una sola vez.
9. Guardar sólo el secreto en un gestor seguro o variable local; nunca en Git ni en logs.

La sesión frontend se almacena localmente bajo `sentinelmonitoria.session`. Logout, cambio de contraseña y refresh invalidan sesiones conforme a las reglas del backend.

## 8. API keys y telemetry

### 8.1 Crear una key

La key debe asociarse a una organización para poder ingerir telemetry. Las nuevas keys se almacenan como digest SHA-256 y la lista nunca devuelve el secreto completo.

Scopes principales:

- `telemetry:write`: permite `POST /api/v1/telemetry`.
- `telemetry:read`: reservado para lecturas futuras; no permite ingesta por sí solo.

### 8.2 Enviar un batch

Ejemplo PowerShell con placeholders:

```powershell
$base = "http://localhost:8000"
$apiKey = "API_KEY_COPIADA_UNA_SOLA_VEZ"
$headers = @{
  Authorization = "Bearer $apiKey"
  "Content-Type" = "application/json"
}
$payload = @{
  metadata = @{
    agent_id = "agent-local-001"
    hostname = "localhost"
    agent_version = "1.0.0"
    platform = "windows"
    architecture = "x64"
    tags = @{ environment = "local" }
  }
  metrics = @(
    @{
      name = "system.cpu.usage"
      value = 42.5
      type = "gauge"
      labels = @{}
      unit = "percent"
    }
  )
  logs = @()
  events = @()
  batch_id = "local-batch-001"
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
  -Uri "$base/api/v1/telemetry" `
  -Method Post `
  -Headers $headers `
  -Body $payload
```

Resultado esperado: HTTP `202`. Consultar estadísticas:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/stats
```

Después de revocar la key, una nueva ingesta con el mismo secreto debe devolver HTTP `401`.

## 9. Configuración y entornos

### Desarrollo

`backend/docker-compose.yml` define explícitamente las variables para localhost:

- `ENVIRONMENT=development`
- `DEBUG=true`
- `API_RELOAD=true`
- `QUEUE_PROVIDER=mock`
- CORS para `localhost:3000` y `127.0.0.1:3000`
- Redis local sin contraseña

Para ejecución directa fuera de Docker:

```powershell
Copy-Item backend/.env.example backend/.env
```

En ese caso los hosts son `POSTGRES_HOST=localhost` y `REDIS_HOST=localhost`.

### Local-production

Este perfil se valida localmente sin AWS y se aproxima más a una ejecución productiva:

- `DEBUG=false` y `API_RELOAD=false`.
- Redis con contraseña.
- Secretos obligatorios.
- Sin Swagger/ReDoc/OpenAPI.
- Sin bind mount del código.
- Migración `alembic upgrade head` antes de Uvicorn.
- `no-new-privileges` y `cap_drop: ALL`.
- Volúmenes separados del stack de desarrollo.

Preparar un archivo local, reemplazar todos los placeholders y no versionarlo:

```powershell
Copy-Item backend/.env.local-production.example backend/.env.local-production
# Editar backend/.env.local-production

docker compose --env-file backend/.env.local-production `
  -f backend/docker-compose.local-production.yml config --quiet

docker compose --env-file backend/.env.local-production `
  -f backend/docker-compose.local-production.yml up -d --build
```

Detener sin borrar datos:

```powershell
docker compose --env-file backend/.env.local-production `
  -f backend/docker-compose.local-production.yml down
```

## 10. Operación diaria

### Estado y logs

```powershell
docker compose -f backend/docker-compose.yml ps
docker compose -f backend/docker-compose.yml logs --tail 200 backend postgres redis
docker compose -f backend/docker-compose.yml logs -f backend
./scripts/test-local.ps1
```

### Detener y reiniciar

```powershell
# Conserva usuarios, telemetry, Redis y logs
docker compose -f backend/docker-compose.yml down

# Arranque posterior
./scripts/start-local.ps1
```

`docker compose down` conserva los volúmenes `postgres_data`, `redis_data` y `backend_logs`.

### Limpieza destructiva

```powershell
./scripts/start-local.ps1 -Clean
```

`-Clean` ejecuta `down -v` y elimina usuarios, organizaciones, tokens y telemetry. No usarlo como solución normal de troubleshooting.

### Migraciones

```powershell
docker exec sentinel-backend alembic upgrade head
docker exec sentinel-backend alembic current
docker exec sentinel-postgres psql -U sentinel -d sentinelmonitoria -tAc "SELECT version_num FROM alembic_version;"
```

## 11. Redis Streams y worker persistente

El flujo durable es opcional. Activarlo con:

```powershell
docker compose -f backend/docker-compose.yml `
  -f backend/docker-compose.redis-worker.yml config --quiet

docker compose -f backend/docker-compose.yml `
  -f backend/docker-compose.redis-worker.yml up -d --build backend worker
```

El worker utiliza consumer groups, `XAUTOCLAIM`, `XACK`, reintentos y dead-letter. Comprobar:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/health
docker exec sentinel-redis redis-cli XPENDING `
  sentinel:stream:telemetry sentinel-telemetry-workers
```

No usar `down -v`. El detalle de la DLQ y el replay idempotente está en `backend/README.md`.

## 12. Pruebas y validación

### Frontend

```powershell
Push-Location frontend
npm ci
npm test
npm run build
npm audit --audit-level=high
Pop-Location
```

Resultado validado: 3 archivos, 9 tests, build Vite 8.1.5 y cero vulnerabilidades reportadas por `npm audit`.

### Backend

```powershell
docker exec sentinel-backend pytest -q
```

Resultado validado: 19 pruebas correctas y una omitida cuando el proveedor es `mock`; la omitida requiere Redis Streams y worker persistente.

### Smoke checks

```powershell
./scripts/test-local.ps1 -RequireFrontend
```

El script comprueba root, health, liveness, readiness, metrics, telemetry health, telemetry stats y frontend.

### Compose y formato

```powershell
docker compose -f backend/docker-compose.yml config --quiet
docker compose -f backend/docker-compose.yml `
  -f backend/docker-compose.frontend.yml config --quiet
docker compose --env-file backend/.env.local-production.example `
  -f backend/docker-compose.local-production.yml config --quiet
git diff --check
```

## 13. Seguridad operativa

- No subir `.env`, tokens, API keys, certificados ni secretos reales.
- `.dockerignore` raíz y `backend/.dockerignore` excluyen secretos, logs y cachés del build.
- Las imágenes verificadas se ejecutan como usuarios no root (`node` y `sentinel`).
- Cambiar secretos antes de cualquier entorno compartido.
- Usar HTTPS fuera de localhost.
- No exponer Redis, Adminer, Redis Commander o Swagger fuera de una red de desarrollo.
- Mantener CORS restringido a los orígenes necesarios.
- No registrar JWTs, API keys ni cuerpos sensibles.
- No usar `down -v`, `-Clean` o endpoints de reset como limpieza rutinaria.

## 14. Troubleshooting

### Docker no responde

```powershell
docker info
docker compose version
./scripts/check-docker.ps1
```

Abrir Docker Desktop, esperar el estado **Engine running** y repetir.

### El frontend no responde

- Confirmar que no haya otro proceso ocupando `3000`.
- Usar `Invoke-WebRequest http://localhost:3000/ -UseBasicParsing`.
- Para modo manual: `Push-Location frontend; npm run dev`.
- Para Docker: detener Vite manual y repetir `./scripts/start-local.ps1 -Build -Frontend`.

### La API aparece desconectada

```powershell
Invoke-RestMethod http://localhost:8000/health
$env:VITE_API_BASE_URL
```

Confirmar que el frontend usa `http://localhost:8000` y que el origen está en `API_CORS_ORIGINS`.

### El backend no inicia

```powershell
docker compose -f backend/docker-compose.yml logs --tail=200 backend
docker compose -f backend/docker-compose.yml ps
```

Después de cambiar `requirements.txt`:

```powershell
docker compose -f backend/docker-compose.yml up -d --build backend
```

### 401 al enviar telemetry

- Confirmar que la API key esté completa, activa y no expirada.
- Confirmar que la key tenga organización y `telemetry:write`.
- Usar `Authorization: Bearer API_KEY`.
- No usar el access JWT de usuario como API key de telemetry.

### 429 inesperado

Comprobar claves `rate_limit:*` en Redis y repetir la prueba sin borrar Redis completo. El backend debe fallar abierto si Redis no está disponible para el rate limiter, según la cobertura validada.

## 15. Agente Vector y E2E

El agente Vector normal está orientado a Linux porque utiliza fuentes de host metrics, journald, archivos y logs Docker. El flujo E2E aislado para Windows + Docker está documentado en `agent/README.md` y conecta:

```text
Vector fixture → FastAPI → Redis Streams → worker → PostgreSQL
```

No ejecutar el Compose auxiliar del agente junto al stack principal sin revisar puertos y redes.

## 16. AWS y límites de esta edición

No se ha desplegado AWS. El diseño offline de `infra/cloudformation/` cubre foundation de red, subnets, security groups, RDS, ElastiCache y ECR. Antes de usarlo en una cuenta real faltan revisión de costes, región, CIDR, IAM, Secrets Manager, NAT, ECS/Fargate, ALB, DNS, ACM, WAF, backups y rollback.

La validación contra una cuenta se ejecutará posteriormente con:

```powershell
aws cloudformation validate-template `
  --template-body file://infra/cloudformation/sentinel-monitoria-foundation.yaml
```

## 17. Checklist de entrega

### Antes de levantar

- [ ] Docker Desktop está ejecutándose.
- [ ] Los puertos requeridos están libres.
- [ ] No existe un `.env` versionable con secretos.
- [ ] Se eligió frontend manual o Docker, no ambos.

### Después de levantar

- [ ] `docker compose ps` muestra PostgreSQL, Redis y backend saludables.
- [ ] `/health`, readiness y telemetry health devuelven estado correcto.
- [ ] Frontend responde HTTP 200.
- [ ] Usuario y organización fueron creados.
- [ ] API key tiene organización y `telemetry:write`.
- [ ] Un batch válido devuelve `202`.

### Antes de compartir o publicar

- [ ] Secretos cambiados y fuera de Git.
- [ ] `npm audit` sin vulnerabilidades altas.
- [ ] Tests y build correctos.
- [ ] `git diff --check` limpio.
- [ ] AWS sigue marcado como pendiente hasta validarlo en cuenta.

## Documentación relacionada

- `README.md`: guía general del proyecto.
- `backend/README.md`: API, auth, API keys, telemetry y Redis worker.
- `docs/operations/local-runbook.md`: operación local y local-production.
- `docs/operations/local-validation-report.md`: evidencia de validación.
- `agent/README.md`: agente Vector y E2E.
- `docs/deployment/cloudformation-plan.md`: plan AWS offline.

# Registro consolidado de implementación y validación

**Última actualización:** 23 de julio de 2026, 21:59 (UTC-05:00)

Este documento consolida el trabajo realizado en SentinelMonitorIA: funcionalidades implementadas, correcciones aplicadas, decisiones técnicas, validaciones locales, límites de AWS y estado final de Git. Es el cierre operativo de la fase local y complementa el [runbook local](local-runbook.md) y el [informe de validación](local-validation-report.md).

## Alcance y límites

- El objetivo fue dejar operativo y comprobado el flujo local con Windows, Docker Desktop, FastAPI, PostgreSQL, Redis, worker y frontend React/Vite.
- No se ejecutaron AWS, CloudFormation, LocalStack ni llamadas reales a Lex, Bedrock, S3, SQS o Knowledge Base.
- No se instalaron dependencias durante la validación final.
- Las acciones automáticas de IA y chatbot permanecen deshabilitadas.
- La arquitectura AWS y sus templates CloudFormation son material preparado y validado offline, no una infraestructura desplegada.

## Cronología resumida

### 1. Revisión inicial del entorno

Se revisaron los scripts operativos y el estado del stack local. El primer smoke check encontró el backend temporalmente `unhealthy` y varios endpoints agotando el timeout mientras Uvicorn esperaba tareas WebSocket durante un reload de WatchFiles. Se reinició únicamente el servicio `backend`, sin borrar volúmenes ni datos.

Después del reinicio quedaron saludables:

- `sentinel-backend`
- `sentinel-postgres`
- `sentinel-redis`
- `sentinel-worker`

### 2. Chatbot operativo provider-neutral

Se implementó un chatbot local reutilizable para una futura integración Lex V2 + Bedrock:

- `POST /api/v1/chat` autenticado con JWT.
- `RulesChatProvider` determinista, sin red ni credenciales externas.
- Contrato `ChatProvider` extensible.
- `CHAT_PROVIDER=rules` independiente de `AI_PROVIDER`.
- Contexto limitado a las alertas visibles de las organizaciones del usuario.
- Campos de contexto allowlisted.
- `CHAT_ENABLE_ACTIONS=false`; el proveedor no ejecuta acciones.
- `ChatWidget` en el frontend con conversación en memoria, sugerencias, estado de consulta, reinicio y diseño responsive.
- `sendChatMessage` en el cliente API.
- Documentación de la futura estrategia: Lex V2 para intenciones/parámetros y Bedrock para generación, explicaciones y RAG.

Archivos principales: `backend/src/api/v1/chat.py`, `backend/src/services/chat/`, `frontend/src/ChatWidget.jsx`, `frontend/src/api.js`, `frontend/src/App.jsx` y `frontend/src/styles.css`.

### 3. AIOps, alertas y notificaciones

Se incorporó la primera capa AIOps asíncrona local:

- Modelos `AIAnalysis`, `Alert` y `NotificationDelivery`.
- Reglas locales para CPU, memoria, logs y eventos.
- Proveedores `rules`, Ollama opcional y Bedrock reservado.
- Workers separados para telemetry, análisis IA y notificaciones.
- Redis Streams opcional con consumer groups, ACK, reintentos y dead-letter.
- Canales de notificación `log`, SMTP, webhook, Slack, Discord, Teams y WebSocket.
- Acknowledge autenticado de alertas, sin ejecutar acciones operativas.
- Configuración `AI_ENABLE_ACTIONS=false` como límite de seguridad de esta fase.

### 4. Validación funcional y hallazgos

Se probaron sesiones efímeras locales para registro, login, `/auth/me`, creación y listado de API keys, ingestión, alertas y chatbot. Las API keys utilizadas en las pruebas se revocaron y las sesiones se cerraron cuando el flujo lo permitió. No se imprimieron tokens, claves ni secretos.

Los primeros hallazgos fueron:

1. `POST /api/v1/telemetry` devolvía `500` por una incompatibilidad entre el nombre ORM `metadata_json` y el argumento `metadata` usado por el servicio.
2. La base local todavía no tenía la columna `telemetrybatch.analysis_enqueued_at` declarada por el modelo.
3. `scripts/test-api.ps1` tenía un error de sintaxis, rutas antiguas y un conteo ficticio de resultados.
4. El WebSocket de alertas transportaba el JWT en `?access_token=...`, por lo que podía quedar en URLs y logs de acceso.

### 5. Correcciones aplicadas

#### Telemetry y esquema

- `backend/src/services/telemetry.py` ahora construye `TelemetryBatch` con `metadata_json`.
- Se añadió `backend/alembic/versions/20260723_0005_reconcile_telemetry_schema.py`.
- La migración comprueba la existencia de la tabla y columna antes de añadirla; no borra datos.
- Se ejecutó `alembic upgrade head` y la base quedó en `20260723_0005 (head)`.

#### Script operativo

Se reescribió `scripts/test-api.ps1` para:

- Usar sintaxis PowerShell válida.
- Consultar las rutas actuales de root, health, liveness, readiness, metrics y telemetry.
- Usar `{}` en el endpoint de telemetry de prueba para activar su payload por defecto.
- Contabilizar resultados reales.
- Diferenciar fallos requeridos de advertencias opcionales.
- Salir con código distinto de cero cuando falla una comprobación requerida.
- No imprimir tokens de ejemplo.

#### WebSocket y logs

- `frontend/src/api.js` abre `/api/v1/alerts/ws` sin query string sensible.
- El primer mensaje del cliente es:

```json
{
  "type": "authenticate",
  "access_token": "ACCESS_JWT"
}
```

- `backend/src/api/v1/alerts.py` acepta ese handshake, valida el JWT y la sesión persistida, aplica un timeout de 10 segundos y limita los datos a las organizaciones del usuario.
- `backend/src/config/logging.py` añade `SensitiveDataFilter` para redactar query tokens y valores Bearer antes de que lleguen a handlers Uvicorn.
- `backend/README.md` documenta el protocolo nuevo y aclara que el JWT no viaja en la URL.

## Contratos funcionales finales

### Autenticación

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

Los access/refresh tokens se persisten por sesión y el refresh es de un solo uso. Logout revoca las sesiones del usuario.

### API keys

- `POST /api/v1/auth/api-keys`
- `GET /api/v1/auth/api-keys`
- `POST /api/v1/auth/api-keys/{token_id}/rotate`
- `DELETE /api/v1/auth/api-keys/{token_id}`

Las keys nuevas se almacenan mediante digest SHA-256, requieren organización para telemetry, tienen scopes y se muestran completas una sola vez. El listado sólo devuelve metadata.

### Telemetry

- `POST /api/v1/telemetry` requiere `Authorization: Bearer API_KEY` y responde `202 Accepted` para un batch válido.
- El batch contiene `metadata` y al menos una métrica, log o evento.
- `GET /api/v1/telemetry/health` y `GET /api/v1/telemetry/stats` son endpoints de observabilidad.

### Alertas y WebSocket

- `GET /api/v1/alerts` devuelve sólo alertas de las organizaciones del usuario.
- `POST /api/v1/alerts/{alert_id}/acknowledge` reconoce una alerta sin ejecutar acciones.
- `WS /api/v1/alerts/ws` requiere el primer mensaje JSON de autenticación descrito arriba.

### Chatbot

- `POST /api/v1/chat` requiere JWT.
- El proveedor local es `rules`.
- El contexto queda limitado por `organization_id`.
- Las acciones devueltas son siempre vacías mientras `CHAT_ENABLE_ACTIONS=false`.

## Configuración local recomendada

```text
ENVIRONMENT=development
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000
API_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
QUEUE_PROVIDER=mock
AI_PROVIDER=rules
AI_ENABLE_ACTIONS=false
CHAT_PROVIDER=rules
CHAT_ENABLE_ACTIONS=false
```

Para el procesamiento durable local se puede usar:

```powershell
docker compose -f backend\docker-compose.yml -f backend\docker-compose.redis-worker.yml up -d backend worker
```

El perfil `local-production` es separado, exige secretos fuertes, usa migraciones Alembic, desactiva debug/reload y no debe exponerse como si fuera producción AWS.

## Comandos de operación y validación

Desde la raíz del repositorio:

```powershell
# Estado del stack
docker compose -f backend\docker-compose.yml -f backend\docker-compose.redis-worker.yml ps

# Smoke read-only del backend y frontend
.\scripts\test-local.ps1 -RequireFrontend

# Smoke API público
.\scripts\test-api.ps1

# Migraciones
docker exec sentinel-backend alembic upgrade head
docker exec sentinel-backend alembic current

# Backend integration suite
docker exec sentinel-backend python -m pytest -vv tests/integration/test_auth_telemetry.py

# Frontend tests y build
Set-Location frontend
npm test
npm run build
Set-Location ..

# Compilación y formato
python -m compileall -q backend/src backend/alembic
git diff --check
```

El smoke API se ejecuta con `.\scripts\test-api.ps1`.

## Evidencia final registrada

| Comprobación | Resultado |
|---|---|
| Docker Compose | backend, PostgreSQL, Redis y worker `healthy` |
| `scripts/test-local.ps1 -RequireFrontend` | 8/8 comprobaciones aprobadas |
| `scripts/test-api.ps1` | 9/9 comprobaciones aprobadas |
| Backend integration suite | 5/5 tests aprobados |
| Frontend Vitest | 9/9 tests aprobados |
| Frontend Vite build | Correcto; Vite `8.1.5`, 22 módulos transformados |
| Python compileall | Correcto |
| Diagnósticos de archivos modificados | Sin errores |
| Alembic | `20260723_0005 (head)` |
| Telemetry autenticado | HTTP `202` |
| WebSocket in-band | Autenticación correcta sin JWT en URL |
| Redacción de logs | Sin valor sensible sin redacción |
| Alertas | HTTP `200`; no había alertas abiertas para acknowledge |
| Chat local | HTTP `200`; provider `rules`, acciones `0` |

Durante las pruebas se observaron warnings de deprecación de Pydantic/`datetime`, pero no bloquearon la operación ni las suites.

## Seguridad y limpieza

- No se deben subir `.env`, credenciales, API keys ni JWT reales.
- No se imprimieron secretos durante las pruebas.
- Las API keys de validación fueron revocadas y las sesiones se cerraron cuando correspondía.
- Quedaron algunas cuentas de registro temporales en la base local porque no se ejecutó una eliminación destructiva. Pueden limpiarse manualmente si se requiere un entorno sin datos de prueba.
- No se utilizó `down -v`, no se borraron volúmenes y no se ejecutó un reset destructivo.
- La corrección de logs evita el JWT en la URL del WebSocket, pero cualquier despliegue no-local todavía requiere HTTPS, proxy seguro, secretos externos y revisión de retención de logs.

## Publicación AWS sin dominio propio

La fase CloudFront fue ampliada para que el dominio predeterminado `*.cloudfront.net` sea el punto público recomendado: S3 sirve el frontend y los behaviors `/api/*`, `/health*`, `/metrics*` y `/api/v1/alerts/ws` enrutan hacia el ALB sin cache. La fase 14 usa una CloudFront Function para el fallback SPA y no aplica respuestas `200` de `index.html` a errores de la API. No requiere Route 53 ni dominio propio; el parámetro `ApiOriginProtocolPolicy=http-only` se usa para el modo de demo sin ACM.

El runtime AWS usa Redis con `TransitEncryptionEnabled=true`, `REDIS_TLS=true` y `rediss://`. Los entornos locales conservan `REDIS_TLS=false`. RDS se inicializa mediante `scripts/run-aws-migration.ps1`, que ejecuta `alembic upgrade head` en una tarea ECS one-off antes de activar los servicios.

Se añadieron herramientas operativas sin credenciales en `scripts/`:

- `aws-preflight.ps1`: verifica cuenta `952763303883`, usuario esperado, región y zonas disponibles cuando se ejecuta explícitamente.
- `validate-cloudformation.ps1`: valida las plantillas mediante CloudFormation.
- `deploy-cloudformation-phases.ps1`: ejecuta los stacks base `00`–`14` por defecto y acepta `19`–`22` individualmente o mediante `-IncludeAiNotifications`, con nombres `sentinel-monitoria-*`, parámetros y Change Sets no ejecutados.
- `build-push-ecr.ps1`: construye y publica imágenes `linux/arm64`.
- `run-aws-migration.ps1`: ejecuta Alembic en ECS.
- `publish-frontend.ps1`: compila con el hostname CloudFront, sincroniza S3 e invalida la distribución.

Para producción con cifrado también entre CloudFront y ALB se requiere un dominio controlado, ACM para el listener HTTPS del ALB y `ApiOriginProtocolPolicy=https-only`. Estas correcciones están preparadas localmente y todavía no se han desplegado en AWS.

## AWS y funcionalidades futuras

No se desplegaron recursos AWS. Quedan preparados o documentados, pero requieren una fase separada:

- Lex V2 + Bedrock para el adaptador cloud del chatbot.
- Bedrock Knowledge Base y vector store persistente para RAG.
- S3 para archivo de telemetry.
- SQS/EventBridge/OpenSearch gestionados.
- Fases CloudFormation `19`–`22`: bucket S3 y rol Bedrock, secreto/SNS de notificaciones, AI worker y notification worker; preparadas offline y opt-in, no desplegadas.
- ECS/Fargate, RDS, ElastiCache, ALB, CloudFront, Route 53, ACM, IAM y Secrets Manager.
- WAF, Multi-AZ completo, réplicas Redis y autoscaling avanzado.
- Validación del agente Vector con journald, archivos host y socket Docker en un Linux real.

La foundation monolítica y las fases CloudFormation `00`–`22` son alternativas de infraestructura; no deben desplegarse juntas en el mismo entorno.

## Estado Git actual

El registro no fija el hash del commit que contiene esta misma actualización para evitar que la documentación quede obsoleta inmediatamente después de publicarla. La integración parte del commit de base `6fa93a3` (`Prepare AWS deployment workflow and runtime fixes`). Para comprobar el estado real después del commit y el push:

```powershell
git status --short --branch
git log -1 --oneline
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

`backend/alembic.ini` forma parte del flujo publicado y permite que las imágenes construidas desde un checkout limpio ejecuten Alembic. Las fases 19–22, sus parámetros, Redis TLS y la documentación ampliada deben permanecer coherentes con el commit que finalmente se publique.

## Referencias

- [README principal](../../README.md)
- [Índice documental](../README.md)
- [Runbook local](local-runbook.md)
- [Informe de validación local](local-validation-report.md)
- [Guía backend](../../backend/README.md)
- [Guía del agente](../../agent/README.md)
- [Plan CloudFormation por fases](../deployment/cloudformation-phased-plan.md)

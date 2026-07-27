# SentinelMonitorIA | Observabilidad — MVP AWS Staging

**Última actualización:** 23 de julio de 2026
**Estado:** staging temporal, validado para demostración; Amplify eliminado y S3 Website activo; no es producción.

Las referencias históricas a Amplify y al worker IA detenido se conservan como contexto del preflight. El estado operativo posterior a la migración está consolidado en la sección **Estado final de la migración** al final de este documento.

Este documento contiene las URLs de conexión y el estado operativo del MVP desplegado en AWS. No incluye contraseñas, API keys, JWT, access keys ni endpoints privados de RDS/Redis.

## URLs de conexión

| Recurso | URL | Uso |
|---|---|---|
| **Frontend recomendado** | [S3 Website HTTP](http://sentinelmonitoria-staging-demo-952763303883-20260726060638.s3-website-us-east-1.amazonaws.com) | Demo completa: registro, login, dashboard y llamadas al ALB. |
| Frontend alternativo | [Amplify Hosting](https://staging.d18ufjvtwidd1p.amplifyapp.com) | Hosting HTTPS del frontend estático. La autenticación no funciona desde este origen mientras la API sea HTTP. |
| **API / ALB** | `http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com` | Base URL de la API pública de staging. Listener actual: HTTP/80. |
| **API Explorer / Swagger** | [Abrir API Explorer](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/docs) | Documentación interactiva de FastAPI para staging. |
| OpenAPI JSON | [openapi.json](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/openapi.json) | Especificación OpenAPI descargable. |
| Health general | [health](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/health) | PostgreSQL, Redis y Telemetry engine. |
| Health API detallado | [api/v1/health](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/health) | Validación detallada de dependencias y recursos. |
| Telemetry health | [telemetry/health](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/telemetry/health) | Estado del motor de telemetry. |
| Metrics | [metrics](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/metrics) | Métricas en formato Prometheus. |

### Acceso AWS

- **Cuenta:** `952763303883`
- **Región:** `us-east-1`
- **Perfil CLI:** `sentinel-monitoria`
- **Cluster ECS:** `sentinel-monitoria-staging`
- **DNS ALB:** `sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com`
- **App Amplify:** `d18ufjvtwidd1p`, branch `staging`
- **Bucket S3 temporal:** `sentinelmonitoria-staging-demo-952763303883-20260726060638`

## Arquitectura AWS de staging

El flujo público actual es:

```text
Navegador
  ├─ S3 Website HTTP ───────────────┐
  └─ Amplify HTTPS (estático)       │
                                     ▼
                         ALB HTTP/80 público
                                     ▼
                         ECS/Fargate backend ARM64
                           ├─ RDS PostgreSQL privado
                           ├─ ElastiCache Redis privado TLS
                           └─ Telemetry engine
                                     │
                         ECS worker Redis 1/1
```

Componentes desplegados:

- VPC, subnets públicas/privadas, NAT instance y security groups.
- ALB público con listener HTTP/80.
- ECS/Fargate ARM64 para backend y worker.
- RDS PostgreSQL privado.
- ElastiCache Redis privado con TLS (`REDIS_TLS=true`).
- ECR, Secrets Manager y CloudWatch Logs.
- S3 Website público temporal para la demostración.
- Amplify Hosting como alternativa de hosting estático.
- Plataforma IA/notificaciones creada de forma opt-in, con sus workers detenidos.

### Estado de servicios ECS

| Servicio | Desired | Running | Estado | Observación |
|---|---:|---:|---|---|
| `sentinel-monitoria-staging-backend` | 1 | 1 | Activo | Imagen `backend:v0.1.1`; API y Swagger operativos. |
| `sentinel-monitoria-staging-worker` | 1 | 1 | Activo | Worker de telemetry con Redis. |
| `sentinel-monitoria-staging-ai-worker` | 0 | 0 | Detenido | Bedrock no autorizado; no se activa. |
| `sentinel-monitoria-staging-notification-worker` | 0 | 0 | Detenido | Notificaciones conservadas en `log`. |

RDS y Redis no tienen URLs públicas de administración. El dashboard valida sus conexiones a través de `/health`; no se publicaron Adminer, Redis Commander ni puertos internos `5432/6379`.

## Usuario demo y flujo correcto de registro

Se creó una cuenta de demostración de aplicación:

- **Username:** `demo.staging.0726065814`
- **Email:** `demo.staging.0726065814@example.com`
- **Rol inicial:** `admin` de su organización
- **Contraseña:** no se registra en Git ni en esta documentación; debe compartirse por un canal seguro.

No se debe usar el usuario AWS para entrar a la aplicación. La aplicación usa sus propios usuarios de `/api/v1/auth/*`.

### Crear una cuenta nueva

1. Abrir el [Frontend recomendado S3 HTTP](http://sentinelmonitoria-staging-demo-952763303883-20260726060638.s3-website-us-east-1.amazonaws.com).
2. Hacer una recarga fuerte con `Ctrl+F5` si existía una versión anterior en caché.
3. Pulsar **Create account**.
4. Completar:
   - `full_name` opcional.
   - `username` obligatorio.
   - `email` válido.
   - `password` de al menos 8 caracteres.
   - `organization_name` obligatorio.
   - `organization_slug` en minúsculas, usando sólo `a-z`, números y guiones.
5. El frontend envía:

```json
{
  "email": "usuario@example.com",
  "username": "usuario",
  "password": "<no documentar>",
  "full_name": "Nombre del usuario",
  "organization_name": "Mi organización",
  "organization_slug": "mi-organizacion"
}
```

6. `POST /api/v1/auth/register` crea el usuario, crea la organización inicial, asigna el rol `admin` y devuelve la sesión JWT.
7. El flujo validado posteriormente es login y `GET /api/v1/auth/me`.

## CORS y causa del fallo de Create account

El origen permitido actualmente es el Website S3 HTTP:

```text
http://sentinelmonitoria-staging-demo-952763303883-20260726060638.s3-website-us-east-1.amazonaws.com
```

La configuración validada es:

- Preflight desde S3: HTTP `200`, `Access-Control-Allow-Origin` correcto.
- Preflight desde Amplify: rechazado, sin `Access-Control-Allow-Origin`.
- El bundle de ambos hosts apunta al ALB HTTP.
- Amplify se sirve por HTTPS; el navegador bloquea HTTPS → HTTP como **mixed content** antes de completar el registro.

Por eso el flujo funcional de esta demo es el enlace S3 HTTP. Añadir el origen Amplify a CORS por sí solo no resuelve el problema: primero se necesita una API HTTPS para el ALB, por ejemplo ALB+ACM con dominio, CloudFront operativo o un proxy HTTPS aprobado.

## API Explorer, Database y Redis

- **API Explorer:** Swagger/OpenAPI está habilitado para `ENVIRONMENT=staging` aunque `DEBUG=false`; producción mantiene la documentación desactivada por defecto.
- **Database:** el botón del dashboard ya no abre `localhost:8080`. Refresca la salud y lleva al panel **Core services**, donde se valida PostgreSQL mediante el backend.
- **Redis:** el botón ya no abre `localhost:8081`. Refresca la salud y lleva al mismo panel, donde se valida Redis mediante `/health`.
- Adminer y Redis Commander sólo existen en Docker local; no están expuestos en el staging ECS.

## Correcciones del copiado de tokens

Se corrigieron dos flujos del frontend:

- **Registro:** cuando el backend devuelve `Validation error`, el frontend ahora muestra cada campo y su causa (`email`, `username`, `password`, `organization_name` u `organization_slug`) en vez de ocultar los detalles.
- Copia de API keys de telemetry.
- Copia de tokens de invitación.

El comportamiento es:

1. Intentar `navigator.clipboard.writeText`.
2. Usar `document.execCommand("copy")` como fallback para HTTP.
3. Si el navegador bloquea ambos métodos, seleccionar automáticamente el token visible en un campo `readonly` y mostrar la instrucción `Ctrl+C`/`⌘+C`.

## Tests, builds y deployments

### Validaciones

- Frontend Vitest: **9/9 tests correctos**.
- Frontend Vite build: correcto.
- Backend `python -m compileall -q src`: correcto.
- `pytest` backend no se ejecutó en el host local porque `pytest` no estaba instalado.
- ALB `/health`: HTTP `200`.
- API Explorer: HTTP `200`, `Content-Type: text/html`.
- OpenAPI JSON: HTTP `200`, título `SentinelMonitorIA`.
- ECS backend: `Desired=1`, `Running=1`.
- S3 y Amplify: raíz y `/dashboard` HTTP `200`.
- Bundle final Amplify: `assets/index-CQU71l5U.js`, `application/javascript`.
- Los bundles finales no contienen `localhost:8080`, `localhost:8081` ni `localhost:8000`.

### Publicaciones relevantes

- Amplify deployment inicial: job `3`.
- Fallback de copia de API keys: job `4`.
- Fallback de token de invitación: job `5`.
- API Explorer y validación Database/Redis: job `6`, estado `SUCCEED`.
- Corrección de mensajes de validación de registro: job `7`, estado `SUCCEED`.
- Backend ECS: imagen ECR `sentinel-monitoria/staging/backend:v0.1.1`, task definition revision `3`.
- Frontend final: bundle `index-DYm-yndH.js` publicado en S3 y Amplify.

## Bloqueos y límites conocidos

### CloudFront / HTTPS

La cuenta AWS devolvió:

```text
Your account must be verified before you can add new CloudFront resources.
```

Por este motivo el MVP usa S3 Website HTTP y el ALB sólo tiene HTTP/80. No se creó dominio propio, Route 53, ACM ni listener HTTPS del ALB.

### Bedrock / Knowledge Base / IA

Bedrock devolvió `authorizationStatus=NOT_AUTHORIZED` para:

- `amazon.titan-embed-text-v2:0`
- `amazon.nova-lite-v1:0`

Consecuencias:

- No se inició la ingesta de Knowledge Base.
- El AI worker permanece en `DesiredCount=0`.
- `AI_ENABLE_ACTIONS=false`.
- Las notificaciones permanecen en `NotificationChannels=log`.

## Seguridad y operación temporal

- No documentar ni subir contraseñas, JWT, API keys, access keys o secretos de Secrets Manager.
- No usar las URLs privadas de RDS/Redis desde un navegador público.
- No presentar Amplify como frontend funcional para autenticación hasta disponer de API HTTPS.
- Staging es temporal: revisar ECS, RDS, Redis, ALB, S3, Amplify y CloudWatch antes de apagar o eliminar recursos para evitar costes.
- El backend y el worker activos tienen coste continuo; los workers de IA/notificaciones permanecen detenidos.

[Volver al índice de deployment](README.md) · [Índice general](../README.md)

## Estado final de la migración

Este bloque es la referencia operativa posterior a la migración autorizada:

- **Frontend:** publicado directamente en el S3 Website `http://sentinelmonitoria-staging-demo-952763303883-20260726060638.s3-website-us-east-1.amazonaws.com`.
- **API:** el bundle se construyó con `VITE_API_BASE_URL=http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com`; el origen S3 está configurado en CORS.
- **Amplify:** la app `d18ufjvtwidd1p` fue eliminada después de validar S3. La eliminación no afectó al bucket Website.
- **Backend ECS:** `Desired=1`, `Running=1`, task definition revision `5`, imagen `backend:v0.1.2`, `CHAT_PROVIDER=lex_bedrock`, locale `es_419` y CORS S3.
- **Lex V2:** bot `XFVQNCQTHX`, alias `67MRXD4DQB` (`staging`), locale construido `es_419`, con `OpenAlertsIntent`, `CriticalAlertsIntent`, `HealthSummaryIntent`, `AssistanceIntent` y `FallbackIntent`. La llamada de reconocimiento validada devolvió `OpenAlertsIntent`.
- **AI worker:** `Desired=1`, `Running=1`, task definition revision `3`, imagen `worker:v0.1.3`, `AI_PROVIDER=bedrock`, `AI_MODEL_ID=amazon.nova-lite-v1:0`, Knowledge Base `0MZLR4E2G7` y `NOTIFICATION_CHANNELS=log`.
- **Notification worker:** permanece en `Desired=0`, `Running=0`; no se activaron emails, webhooks ni otros destinos.
- **RDS y Redis:** no se modificaron sus recursos ni su configuración de infraestructura.

### Limitación actual de Bedrock

La cuenta mantiene `NOT_AUTHORIZED` para `amazon.nova-lite-v1:0` y `amazon.titan-embed-text-v2:0`. Por ello el AI worker está activo en modo degradado seguro: ejecuta reglas determinísticas, crea `AIAnalysis` y `Alert`, usa contexto local cuando falla la recuperación de Knowledge Base y registra el error del proveedor sin reintentos infinitos. La explicación generada por Nova Lite y el contexto RAG quedarán disponibles cuando AWS autorice ambos modelos; no se deben presentar como validados todavía.

### Demo validada tras la migración

Se envió un batch aislado con CPU `97%`, memoria `96%` y un log `error`. El worker generó un `AIAnalysis` con hallazgos/recomendaciones y una alerta `high` abierta; el chat autenticado respondió desde la organización de prueba con `provider=lex_bedrock` y una consulta de alertas abiertas. La API key temporal utilizada para la ingesta fue revocada después de la prueba.

### Validación técnica final

- Docker Desktop/daemon y Compose: disponibles; build ARM64 backend/worker completado y publicado en ECR con tags inmutables `v0.1.2`/`v0.1.3`.
- Smoke local: backend pasa todos los endpoints requeridos; frontend local permanece opcional.
- Smoke staging: ALB y S3 Website responden HTTP `200` en las rutas verificadas.
- Backend tests: `19 passed, 1 skipped` (el skip corresponde a la integración Redis worker con `QUEUE_PROVIDER=redis`).
- Frontend build Vite: correcto; el bundle remoto contiene la URL del ALB.
- CloudFormation: fases IAM, backend ECS y AI worker desplegadas correctamente con el perfil `sentinel-monitoria`.
- El publicador `scripts/publish-frontend.ps1` ya usa S3 Website + ALB, valida que el bucket tenga Website configuration y no intenta crear invalidaciones CloudFront.

S3 Website y ALB siguen siendo HTTP temporales. CloudFront/HTTPS, autorización de modelos Bedrock y la ingesta efectiva de la Knowledge Base siguen siendo pendientes de infraestructura o cuenta, no deben confundirse con el flujo funcional ya validado.
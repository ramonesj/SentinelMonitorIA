# SentinelMonitorIA
## Dossier técnico para el jurado AWS y Código Facilito

**Edición:** 1.0<br>
**Entorno:** AWS staging en `us-east-1`<br>
**Propósito:** evaluación técnica, demostración en vivo y revisión del flujo de código<br>
**Estado:** staging temporal validado; no es producción

> Este dossier reúne el alcance que puede revisar el jurado de AWS y el jurado de Código Facilito: arquitectura, operación, código, seguridad, evidencia y recorrido de demostración.

## 1. Resumen ejecutivo

SentinelMonitorIA es un MVP de observabilidad y AIOps que recibe métricas, logs y eventos, los persiste, los analiza con reglas determinísticas y genera alertas visibles desde un dashboard.

El recorrido AWS validado es:

```text
Frontend S3 Website
  → ALB HTTP/80
  → ECS backend
  → RDS PostgreSQL + Redis TLS
  → telemetry worker
  → AI worker
  → AIAnalysis + Alert
```

Para la conversación, Amazon Lex V2 identifica intenciones y estructura las solicitudes en `es_419`. No se utiliza Bedrock ni embeddings en esta demostración. Las respuestas operativas usan reglas locales y las acciones automáticas están deshabilitadas.

## 2. Acceso del jurado

### URLs

| Recurso | URL | Uso |
|---|---|---|
| Frontend recomendado | http://sentinelmonitoria-staging-demo-952763303883-20260726060638.s3-website-us-east-1.amazonaws.com | Login y dashboard |
| API base | http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com | Backend FastAPI |
| Swagger | http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/docs | Contratos y pruebas |
| Health | http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/health | Salud de dependencias |
| Telemetry health | http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/telemetry/health | Estado de ingestion |
| Metrics | http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/metrics | Prometheus |

Usar el S3 Website HTTP, no Amplify HTTPS. La API staging está publicada en HTTP/80; desde HTTPS el navegador puede bloquear las llamadas por mixed content.

### Cuenta de aplicación

Estas credenciales corresponden a la aplicación demo, no a la cuenta AWS:

| Campo | Valor |
|---|---|
| Usuario | `demo.staging.0726065814` |
| Email | `demo.staging.0726065814@example.com` |
| Contraseña | `S3ntinel!Demo2026` |
| Rol | `admin` |
| Organización ID | `871268b3-3238-422b-aeb6-19e06f4bf5a8` |

### API key del productor sintético

La API key tiene únicamente `telemetry:write` y sólo se usa contra `/api/v1/telemetry`; no sirve para `/api/v1/chat` ni `/api/v1/alerts`.

- Nombre: `Local telemetry agent`
- Scope: `telemetry:write`
- Organización: `871268b3-3238-422b-aeb6-19e06f4bf5a8`

```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhOGM4MzM0Zi01MGZmLTQ5N2QtODVkZC03YTAwYjA2NWI2ZDAiLCJ1c2VybmFtZSI6ImRlbW8uc3RhZ2luZy4wNzI2MDY1ODE0IiwidHlwZSI6ImFwaV9rZXkiLCJuYW1lIjoiTG9jYWwgdGVsZW1ldHJ5IGFnZW50Iiwib3JnIjoiODcxMjY4YjMtMzIzOC00MjJiLWFlYjYtMTllMDZmNGJmNWE4Iiwic2NvcGVzIjpbInRlbGVtZXRyeTp3cml0ZSJdLCJleHAiOjE4MTY2NDEyMjEsImlhdCI6MTc4NTEwNTIyMSwianRpIjoiNmNkMzk2NzUtMTllNy00ZWM0LWE5YzItMjJmOWJkM2VlNWE4In0.qoZHpYKu2l3HNfuXCQGTcx2qIlrQ32a07ELBIZ13zZ4
```

> Son credenciales de staging entregadas expresamente para evaluación. No reutilizarlas en producción. Rotarlas o revocarlas después del jurado y no compartir este PDF públicamente sin retirar los secretos.

## 3. Recorrido de la demostración

1. Abrir el frontend S3 y hacer `Ctrl+F5`.
2. Iniciar sesión con la cuenta demo.
3. Mostrar el estado saludable de PostgreSQL, Redis y telemetry.
4. Abrir **Ask Sentinel** y preguntar: `¿Cuántas alertas abiertas hay?`.
5. Mostrar el footer `Lex V2 · es_419 · flujo estructurado · lectura segura`.
6. Consultar `Resume las alertas críticas` y `Revisa el estado de telemetry`.
7. Actualizar la vista de alertas y abrir una alerta `high` del agente sintético.
8. Mostrar CPU/memoria sintéticas, `rule_id=metric.cpu.high` y `analysis_id`.
9. Mostrar que el notification worker está apagado y no hay entregas externas.

## 4. Lex V2 estructurado

| Propiedad | Valor validado |
|---|---|
| Bot | `XFVQNCQTHX` |
| Alias | `67MRXD4DQB` (`staging`) |
| Locale | `es_419` |
| Intent probado | `OpenAlertsIntent` |
| Confianza observada | `0.9` |
| Estado de diálogo | `Close` |

Intenciones disponibles: `OpenAlertsIntent`, `CriticalAlertsIntent`, `HealthSummaryIntent`, `AssistanceIntent` y `FallbackIntent`.

Lex V2 identifica la intención, valida slots cuando son necesarios y entrega una petición estructurada al backend. No se invoca Bedrock, no se usan embeddings y no se ingiere la Knowledge Base. `lex_bedrock` es un identificador interno heredado; la UI lo presenta como Lex V2 para no sugerir que Bedrock esté activo.

## 5. Productor sintético EC2

| Propiedad | Valor |
|---|---|
| Instancia | `test-redes` |
| Instance ID | `i-0c56b84145cd08d22` |
| Tipo | `t3.micro` |
| Sistema | Amazon Linux 2023, `x86_64` |
| Administración | SSM, sin SSH ni puertos nuevos |
| Usuario | `sentinel-demo` |
| Script remoto | `/opt/sentinel-mvp/mvp-demo-producer.py` |
| Servicio | `sentinel-mvp-demo-producer.service` |
| Entorno | `/etc/sentinel-mvp/producer.env` con modo `0600` |
| Agent ID | `ec2-test-redes-synthetic` |

El productor no genera carga real. Envía valores sintéticos al analizador:

- Normal: CPU `25–55%`, memoria `35–65%`, log `info`, evento `info`.
- Incidente: CPU `96%`, memoria `94%`, log `error`, evento `high`.
- Normal cada `30–60` segundos.
- Incidente cada `300–600` segundos, es decir, `5–10` minutos.
- `batch_id` UUID por envío.
- Reintentos limitados y probes de health después de cada batch.

Tags de todos los batches:

```json
{
  "environment": "mvp-demo",
  "synthetic": "true",
  "source": "continuous-demo"
}
```

Límites systemd:

```ini
User=sentinel-demo
Restart=always
CPUQuota=5%
MemoryMax=128M
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
```

## 6. Flujo telemetry → análisis → alerta

```text
EC2 producer
  → POST /api/v1/telemetry (202)
  → TelemetryBatch, Metric, LogEntry y Event
  → Redis Streams / ai_analysis
  → ECS AI worker
  → RuleBasedAnomalyDetector
  → AIAnalysis
  → Alert high
  → notifications sin consumer activo
```

El detector dispara findings cuando CPU o memoria con unidad `percent` alcanzan `90%`, cuando aparece un log `error`/`fatal` o cuando un evento es `high`/`critical`. El incidente controlado genera alertas de inteligencia sin invocar un modelo generativo.

## 7. Estado ECS y seguridad

| Servicio | Desired | Running | Estado |
|---|---:|---:|---|
| Backend | 1 | 1 | Activo, revisión `5` |
| Telemetry worker | 1 | 1 | Activo |
| AI worker | 1 | 1 | Activo, revisión `3` |
| Notification worker | 0 | 0 | Apagado intencionalmente |

- `AI_ENABLE_ACTIONS=false`.
- Cola `notifications=0`.
- No se envían emails, Slack, Discord, Teams ni webhooks.
- RDS y Redis no cambiaron su infraestructura; sólo se persistieron datos sintéticos de demo.
- No se modificaron NAT, security groups, rutas ni puertos de la EC2.
- El productor usa un usuario no root y el secreto remoto está en un archivo `root:root` con permisos `0600`.

## 8. Evidencias verificadas

| Evidencia | Resultado |
|---|---|
| Incidente one-shot | HTTP `202` |
| Health general | HTTP `200` |
| Telemetry health | HTTP `200`, `healthy` |
| Metrics | HTTP `200` |
| Chat autenticado | HTTP `200`, conversación creada |
| Lex | `OpenAlertsIntent`, confianza `0.9` |
| Alertas demo | `high`, `metric.cpu.high`, `analysis_id` presente |
| Notification worker | `0/0` |
| Productor | systemd `enabled/active` |
| Límites EC2 | CPU `5%`, memoria `128 MiB` |
| Integridad | hash remoto igual al local; `git diff --check` correcto |

## 9. Criterios AWS

- Arquitectura AWS desplegada con S3 Website, ALB, ECS, RDS, Redis TLS, ECR, Secrets Manager y CloudWatch.
- Operación controlada con ECS desired/running counts verificables.
- Acceso a EC2 mediante SSM, sin abrir SSH ni puertos de entrada.
- IAM y API keys con permisos separados.
- Coste optimizado reutilizando la EC2 existente en lugar de crear un ECS producer permanente.
- Notificaciones y acciones automáticas apagadas para evitar efectos externos.
- Estado de Bedrock documentado como `NOT_AUTHORIZED`; no se presenta como activo.

## 10. Criterios Código Facilito

- Backend FastAPI con contratos Pydantic y autenticación JWT/API key.
- Frontend React/Vite con proveedor de chat visible y configuración de build.
- Productor Python sólo con biblioteca estándar.
- Servicio systemd no root, limitado y reiniciable.
- Flujo asíncrono telemetry → análisis → alertas.
- Identificadores, tags y batches reproducibles.
- Scripts de instalación y publicación automatizados.
- Validación de AST/diagnósticos, build frontend y `git diff --check`.
- Documentación de arquitectura, operación, errores, seguridad y rollback.

## 11. Troubleshooting rápido

### Chat HTTP 401

Usar S3 HTTP, hacer `Ctrl+F5`, cerrar sesión e iniciar de nuevo. Si es necesario, ejecutar en DevTools:

```javascript
localStorage.removeItem("sentinelmonitoria.session");
location.reload();
```

La API key del productor no sirve para el chat.

### No aparece alerta

El heartbeat normal no genera alertas. Esperar la ventana de 5–10 minutos o ejecutar el smoke incident por SSM. Después de un `202`, actualizar el dashboard y esperar unos segundos al AI worker.

### No hay notificaciones

Es intencional: notification worker `0/0`, `AI_ENABLE_ACTIONS=false` y cola `notifications=0`.

## 12. Coste y cierre

La EC2 `t3.micro` ya estaba encendida; el coste marginal del productor es prácticamente cero. No se creó un servicio ECS adicional para producir telemetry.

Después de la evaluación:

1. Ejecutar `systemctl disable --now sentinel-mvp-demo-producer.service` por SSM.
2. Revocar la API key `Local telemetry agent`.
3. Desactivar o cambiar el usuario demo.
4. Retirar los secretos de los documentos si el repositorio se publica.
5. Revisar ECS, RDS, Redis, ALB, S3, CloudWatch y EC2 para controlar costes.

## 13. Archivos principales

- `scripts/mvp-demo-producer.py`: productor, batches, intervalos y reintentos.
- `scripts/install-mvp-demo-producer.ps1`: instalación por SSM y systemd.
- `frontend/src/ChatWidget.jsx`: etiqueta dinámica Lex/local.
- `scripts/publish-frontend.ps1`: build y publicación S3.
- `backend/src/api/v1/telemetry.py`: autenticación e ingesta.
- `backend/src/services/ai/analyzer.py`: reglas de anomalías.
- `backend/src/services/chat/providers.py`: Lex y fallback.
- `README.md`: fuente general de documentación.

# Arquitectura de SentinelMonitorIA: observabilidad, AIOps y alertas

Esta sección documenta dos superficies relacionadas pero distintas: el sistema local validado y la arquitectura AWS preparada para una futura instalación. La extensión IA/notificaciones ya tiene contratos, workers, persistencia y fases declarativas; el diseño AWS se ha comprobado offline y no implica que exista un entorno AWS desplegado.

## Documentos

- [Arquitectura AWS en Markdown](sentinelmonitoria-aws-architecture.md): componentes, IA, alertas, relaciones, red y fases.
- [Diagrama completo de infraestructura AWS](sentinelmonitoria-aws-infrastructure.md): estado real de staging, arquitectura objetivo, flujos, seguridad y operación.
- [Diagrama AWS editable](sentinelmonitoria-aws-architecture.drawio): fuente Draw.io editable con formas/estilos de recursos AWS.
- [Arquitectura del agente](agent-architecture.md): Vector, fuentes de telemetría, transformaciones, buffers y sink HTTP.
- [Plan de despliegue AWS](../deployment/README.md): relación entre la arquitectura y los stacks CloudFormation.
- [Operación local](../operations/local-runbook.md): procedimientos para el entorno que sí está validado.

## Arquitectura local validada

El recorrido local es:

```text
React/Vite :3000
      │ HTTP + CORS + Bearer JWT
      ▼
FastAPI :8000 ───────► PostgreSQL :5432
      │
      ├──────────────► Redis :6379
      └──────────────► Cola mock o Redis Streams
                              │
                              ▼
                         Worker telemetry
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              AI analysis          Notifications
              rules/Ollama          log/webhook/SMTP
```

El usuario crea una organización, genera una API key, conecta un agente y envía batches a `POST /api/v1/telemetry`. El backend valida la key, organización, expiración y scopes; persiste el batch y lo entrega al proveedor de cola local. Con Redis Streams, el worker confirma la persistencia y publica una referencia en `ai_analysis`; los workers de análisis y notificaciones procesan después sin bloquear la respuesta `202` de telemetry.

### Capacidades implementadas

- Detección determinística de CPU, memoria porcentual, logs `error/fatal` y eventos `high/critical`.
- Correlación básica por organización y batch mediante `AIAnalysis` y una clave de deduplicación.
- Contexto local acotado al batch; no se envían logs a un modelo por defecto.
- Ollama opcional para explicaciones en lenguaje natural.
- Adapter opcional de Bedrock Converse y Retrieve cuando se configura `AI_PROVIDER=bedrock`.
- Alertas persistidas, acknowledge autenticado y entregas idempotentes.
- Canales `log`, Email/SMTP, webhook, Slack, Discord y Microsoft Teams.
- Endpoint WebSocket `/api/v1/alerts/ws` para cambios de alertas; en múltiples tareas se debe añadir pub/sub compartido.
- Acciones automáticas desactivadas permanentemente en esta fase (`AI_ENABLE_ACTIONS=false`).

## Arquitectura AWS objetivo

La propuesta AWS se sitúa en `us-east-1` y usa:

- VPC `10.42.0.0/16`.
- Subnets públicas `10.42.1.0/24` y `10.42.2.0/24`.
- Subnets privadas `10.42.11.0/24` y `10.42.12.0/24`.
- Internet Gateway y una instancia NAT ARM64 `t4g.micro` con EIP para salida controlada.
- ALB público hacia ECS/Fargate ARM64 en el puerto `8000`, con health check `/health`.
- ECS backend, worker telemetry, AI worker y notification worker separados.
- RDS PostgreSQL y ElastiCache Redis en la red privada.
- ECR para la imagen compartida por backend, telemetry, IA y notificaciones.
- S3 privado para archivo/contexto IA y S3/CloudFront para el frontend.
- Bedrock Runtime con Nova Lite para explicaciones, Knowledge Base administrada con Titan Embeddings V2 y S3 Vectors como vector store RAG.
- CloudWatch para logs, Secrets Manager para credenciales y SNS como canal AWS opcional.
- Route 53, ACM, HTTPS y registros DNS como borde opcional cuando exista un dominio real.

### Relaciones principales

```text
Usuarios/agentes
       │
       ▼
CloudFront ─────► S3 (frontend estático)
       │
       └────► ALB público ─────► ECS backend :8000
                                      │
                              Redis Streams
                                      │
       ┌──────────────────────────────┼─────────────────────────────┐
       ▼                              ▼                             ▼
Worker telemetry                 AI worker                 Notification worker
       │                         reglas + Bedrock             canales externos
       ├────► PostgreSQL          │                             │
       └────► ai_analysis        ├────► PostgreSQL              └────► SNS/SES/webhooks
                                  └────► S3/Knowledge Base
```

La salida de los recursos privados usa la ruta privada hacia la instancia NAT y su EIP. Los grupos de seguridad deben limitar ALB → backend, workers → RDS/Redis y las salidas necesarias; no se debe convertir RDS ni Redis en endpoints públicos.

## Correspondencia local/AWS

| Capacidad | Local | AWS |
|---|---|---|
| Reglas y análisis | Python en `ai_analysis_worker` | ECS/Fargate ARM64 en fase 21 |
| LLM | Ollama opcional | Bedrock Converse |
| RAG | Contexto del batch; vector store local futuro | S3 + Knowledge Base Bedrock + S3 Vectors |
| Persistencia | PostgreSQL + Redis Streams | RDS + ElastiCache |
| Alertas | PostgreSQL, WebSocket y workers | RDS, ECS, SNS/SES/adaptadores |
| Secretos | `.env` local ignorado, sin credenciales productivas | Secrets Manager + IAM task roles |

## Decisiones y límites

- La foundation monolítica y los 23 stacks modulares `00`–`22` son opciones alternativas, no capas para desplegar simultáneamente.
- `QUEUE_PROVIDER=mock` conserva el flujo local básico; la extensión IA/notificaciones requiere el override Redis worker.
- Bedrock se usa para explicación y recuperación, no sustituye las reglas ni la cola de telemetry.
- La fase 19 crea el Knowledge Base Bedrock, su Data Source S3 y el bucket/índice S3 Vectors; el índice usa Titan Embeddings V2 y el AI worker recupera contexto mediante el export de CloudFormation.
- OpenSearch gestionado fuera de S3 Vectors, SQS/EventBridge, WAF, Multi-AZ completo, réplicas Redis, NAT Gateway y autoscaling avanzado quedan fuera del despliegue inicial.
- Los secretos no se almacenan en templates, parámetros ni README; se inyectan mediante Secrets Manager y variables locales protegidas.
- La existencia de un template no significa que haya sido validado por CloudFormation ni que se haya creado un recurso AWS.

## Cómo leer el diagrama

1. La capa de borde representa usuarios, CloudFront, S3 y el dominio opcional.
2. La VPC muestra explícitamente CIDR, subnets públicas/privadas, tablas de rutas, IGW y NAT.
3. La capa de aplicación separa ALB, backend, telemetry worker, AI worker y notification worker.
4. La capa IA muestra reglas, Bedrock opcional, contexto S3/Knowledge Base y alertas.
5. La capa de notificaciones muestra Email, Slack, Discord, Teams, WebSocket y Webhooks.
6. Las fases `00`–`22` del plan modular reflejan el orden lógico, no una orden de despliegue ya ejecutada.

[Volver al índice documental](../README.md)

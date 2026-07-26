# Despliegue e infraestructura AWS

**Última actualización:** 23 de julio de 2026, 21:59 (UTC-05:00)

Esta sección documenta cómo está organizada la infraestructura declarativa de SentinelMonitorIA. El repositorio conserva dos alternativas: una foundation CloudFormation monolítica y una implementación modular por fases. Ambas describen el mismo entorno lógico y **no deben desplegarse juntas**.

## Documentos principales

- [Plan modular por fases](cloudformation-phased-plan.md): dependencias, contratos, exports/imports y orden `00`–`22`.
- [Estimación mensual AWS](aws-monthly-estimate.md): escenario staging ARM64, coste de tres días y foundation mínima.
- [Plan de foundation](cloudformation-plan.md): alternativa monolítica y decisiones de la infraestructura inicial.
- [README de la foundation](../../infra/cloudformation/README.md): template, parámetros y uso previsto.
- [README de templates modulares](../../infra/cloudformation/phases/README.md): catálogo de fases y validaciones offline.
- [Matriz de parámetros](../../infra/cloudformation/phases/parameters.example.json): valores de ejemplo sin credenciales reales.
- [Scripts de despliegue](../../scripts/): preflight, validación CloudFormation, stacks, ECR ARM64, migración ECS y publicación frontend.
- [Arquitectura AWS](../architecture/sentinelmonitoria-aws-architecture.md): vista de componentes y relaciones.
- [Diagrama editable](../architecture/sentinelmonitoria-aws-architecture.drawio): representación visual de la arquitectura.

## Alternativas de implementación

### Foundation monolítica

La foundation existente agrupa la base de red, NAT, grupos de seguridad, RDS, Redis y ECR en un template principal:

- Template: `infra/cloudformation/sentinel-monitoria-foundation.yaml`.
- Documentación: [infra/cloudformation/README.md](../../infra/cloudformation/README.md).
- Plan: [cloudformation-plan.md](cloudformation-plan.md).

Es apropiada como referencia compacta o para un entorno inicial controlado. No debe combinarse con los stacks modulares para la misma VPC o los mismos servicios.

### Stacks modulares

La alternativa modular separa responsabilidades y permite revisar cada contrato antes de avanzar:

| Fase | Responsabilidad | Estado |
|---:|---|---|
| `00` | VPC, subnets, tablas de rutas e Internet Gateway | Base |
| `01` | NAT instance ARM64, EIP y salida privada | Base |
| `02` | Security groups | Base |
| `03` | IAM de ejecución, tareas y despliegue | Base |
| `04` | ECR backend y worker | Aplicación |
| `05` | RDS PostgreSQL privado | Datos |
| `06` | ElastiCache Redis privado | Datos |
| `07` | Secrets Manager | Seguridad |
| `08` | CloudWatch log groups y observabilidad | Operación |
| `09` | ALB y target group HTTP | Entrada |
| `10` | ECS cluster | Aplicación |
| `11` | ECS/Fargate backend | Aplicación |
| `12` | ECS/Fargate worker | Aplicación |
| `13` | S3 para frontend estático | Frontend |
| `14` | CloudFront | Frontend |
| `15` | Route 53 hosted zone opcional | Dominio |
| `16` | ACM certificates opcionales | HTTPS |
| `17` | Listener HTTPS del ALB opcional | HTTPS |
| `18` | Registros Route 53 opcionales | Dominio |
| `19` | Plataforma IA: S3, logs y rol Bedrock | Inteligencia |
| `20` | Plataforma notificaciones: secreto, SNS y logs | Notificaciones |
| `21` | Worker ECS de análisis y alertas | Inteligencia |
| `22` | Worker ECS de entregas de notificaciones | Notificaciones |

El catálogo completo, los parámetros y los exports/imports se mantienen en [`infra/cloudformation/phases/README.md`](../../infra/cloudformation/phases/README.md).

## Orden y contratos

1. Crear la red y la salida privada (`00`–`01`).
2. Aplicar seguridad, IAM y ECR (`02`–`04`).
3. Crear datos, secretos y observabilidad (`05`–`08`).
4. Crear entrada y cluster ECS (`09`–`10`).
5. Publicar imágenes ARM64 en ECR.
6. Si se habilita IA/notificaciones, crear sus recursos base (`19`–`20`) con el mismo proyecto, entorno y región.
7. Crear las task definitions `11`, `12`, `21` y `22` con `DesiredCount=0`, ejecutar la migración Alembic como tarea ECS one-off y después activar los cuatro servicios.
8. Crear S3 y CloudFront (`13`–`14`), actualizar CORS con el hostname CloudFront y publicar `frontend/dist`.
9. Añadir dominio y HTTPS sólo después de confirmar dominio, región y certificados (`15`–`18`).

El despliegue conserva `00`–`14` como recorrido predeterminado. Las fases `19`–`22` se habilitan individualmente o mediante `-IncludeAiNotifications`; no se ejecutan automáticamente junto con la base para evitar arrancar workers antes de las migraciones. Cada stack exporta valores con el prefijo del proyecto y del entorno, y los consumidores los importan mediante contratos explícitos. La matriz de parámetros debe revisarse como un conjunto; no se deben mezclar valores de foundation con los de fases modulares.

## Costes documentados

- Staging ARM64 estimado: **USD 75–90/mes**.
- Tres días de ejecución estimados: **USD 7.40–8.88**, antes de créditos, impuestos y variaciones de tráfico.
- Foundation solamente: **USD 35–55/mes**.

Estos importes son estimaciones de planificación, no facturas ni garantías de precio. Antes de crear recursos deben revisarse región, horas, almacenamiento, snapshots, tráfico, logs, NAT, CloudFront, S3, Bedrock, Knowledge Base, S3 Vectors y créditos disponibles. Las fases `21` y `22` añaden dos servicios ECS y sus logs; mantener `DesiredCount=0` durante preparación y `AiProvider=rules`/`NotificationChannels=log` durante la prueba reduce el coste variable. Bedrock y el vector store añaden coste variable adicional; mantener `AiProvider=rules` reduce el coste de staging.

## Inteligencia y notificaciones

- Local: `AI_PROVIDER=rules` no hace llamadas externas; `ollama` es opcional y usa el endpoint local configurado.
- AWS: `AI_PROVIDER=bedrock` usa el rol IAM de la fase 19 y `AI_MODEL_ID`; la Knowledge Base se provisiona en la fase 19 y su ID llega al AI worker mediante el export `AiKnowledgeBaseId`.
- La fase 21 ejecuta `src.workers.ai_analysis_worker` y la fase 22 ejecuta `src.workers.notification_worker`.
- El valor seguro inicial es `NotificationChannels=log`; la fase 21 lo impone para el AI worker. Email, Slack, Discord, Teams y webhooks sólo corresponden a los canales de notificación configurados explícitamente fuera de esta fase.
- Las acciones automáticas permanecen desactivadas y no se ejecutan comandos sobre la infraestructura desde el worker.

## Seguridad y operación

- RDS, Redis, ECS y secretos se mantienen en subnets privadas; el ALB es el punto de entrada público.
- Las credenciales de RDS/Redis, `SECRET_KEY` y `JWT_SECRET_KEY` deben residir en Secrets Manager o en el mecanismo seguro equivalente; nunca en Git ni en parámetros compartidos.
- Los templates usan IAM y security groups separados para limitar el tráfico entre capas.
- Route 53/ACM/HTTPS permanecen opcionales hasta disponer de un dominio administrado por el equipo.
- La NAT instance reduce el coste frente a NAT Gateway, pero requiere evaluar disponibilidad, parcheo y capacidad antes de producción.
- La propuesta inicial no incluye WAF, SQS gestionado, Multi-AZ completo, réplicas Redis ni autoscaling avanzado.

Para la operación real disponible hoy, consultar el [runbook local](../operations/local-runbook.md) y el [informe de validación local](../operations/local-validation-report.md).

## Validación y límites de ejecución

Comprobaciones offline realizadas:

- Parseo local correcto de los 23 templates YAML.
- Matriz JSON de parámetros válida.
- Paridad de parámetros entre templates y ejemplos.
- Resolución de imports cross-stack contra exports definidos.
- `git diff --check` correcto y escaneo sin credenciales reales.
- Scripts PowerShell de preflight, validación, despliegue, ECR, migración y frontend preparados, pero no ejecutados contra AWS.
- `cfn-lint` no se ejecutó porque no está instalado y no se instalaron dependencias.

No se ejecutaron comandos de AWS, incluyendo `aws cloudformation validate-template`, `create-stack` o `deploy`. Esta documentación no autoriza ni implica un despliegue; cualquier ejecución debe ser una decisión explícita y precedida por revisión de seguridad, costes, backups y rollback.

[Volver al índice documental](../README.md)

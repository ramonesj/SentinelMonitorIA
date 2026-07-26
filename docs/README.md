# Documentación de SentinelMonitorIA

**Última actualización:** 23 de julio de 2026, 21:59 (UTC-05:00)

Este índice reúne la documentación vigente del repositorio. El flujo local con Windows + Docker y el MVP AWS staging en `us-east-1` tienen validaciones separadas. El staging es temporal, usa S3 Website HTTP y ALB HTTP/80, y no debe considerarse una infraestructura de producción.

## Inicio por objetivo

| Necesidad | Documento recomendado |
|---|---|
| Ejecutar el proyecto localmente | [README principal](../README.md) |
| Entender la arquitectura completa | [Índice de arquitectura](architecture/README.md) |
| Consultar el diagrama editable AWS | [Diagrama Draw.io](architecture/sentinelmonitoria-aws-architecture.drawio) |
| Revisar el despliegue por fases | [Índice de despliegue](deployment/README.md) |
| Operar y conectar el MVP AWS staging | [MVP AWS staging](deployment/mvp-staging.md) |
| Operar y validar el entorno local | [Runbook local](operations/local-runbook.md) · [Informe de validación](operations/local-validation-report.md) · [Registro consolidado de entrega](operations/project-delivery-record.md) |
| Usar el backend o el agente | [Guía del backend](../backend/README.md) · [Guía del agente](../agent/README.md) |
| Leer el manual ejecutivo | [Manual Markdown](manual/SentinelMonitorIA-Manual-Ejecutivo.md) · [Manual PDF](manual/SentinelMonitorIA-Manual-Ejecutivo.pdf) |

## Arquitectura

- [Arquitectura local y AWS](architecture/README.md): alcance, componentes, redes, flujos y decisiones.
- [Vista AWS en Markdown](architecture/sentinelmonitoria-aws-architecture.md): versión legible y fallback del diagrama.
- [Diagrama AWS editable](architecture/sentinelmonitoria-aws-architecture.drawio): archivo editable en diagrams.net/draw.io con estilos de recursos AWS.
- [Arquitectura del agente](architecture/agent-architecture.md): Vector, fuentes, transformaciones y sink HTTP.

La arquitectura AWS documentada usa `us-east-1`, una VPC `10.42.0.0/16`, subnets públicas y privadas en dos zonas, ECS/Fargate ARM64, ALB, RDS PostgreSQL privado, Redis privado, ECR, Secrets Manager, CloudWatch, S3 y CloudFront. Añade workers de análisis y notificaciones, Bedrock Nova Lite, una Knowledge Base con Titan Embeddings V2 y S3 Vectors como vector store. Route 53, ACM, HTTPS y DNS se mantienen como fases opcionales hasta disponer de un dominio real.

## Despliegue e infraestructura

- [Índice de despliegue](deployment/README.md): alternativas, orden y límites.
- [Plan CloudFormation por fases](deployment/cloudformation-phased-plan.md): contrato de los 23 stacks modulares `00`–`22`.
- [Implementación IA y alertas](../backend/README.md#flujo-de-ia-y-alertas): workers, proveedores local/Bedrock y canales de notificación.
- [Plan CloudFormation foundation](deployment/cloudformation-plan.md): alternativa monolítica existente.
- [Estimación mensual AWS](deployment/aws-monthly-estimate.md): escenarios ARM64 staging y foundation.
- [README de la foundation](../infra/cloudformation/README.md): template monolítico, parámetros y advertencias.
- [README de fases](../infra/cloudformation/phases/README.md): templates, exports/imports y orden de despliegue.
- [Parámetros de ejemplo por fase](../infra/cloudformation/phases/parameters.example.json): matriz sin credenciales reales.

La foundation monolítica y los stacks modulares son alternativas excluyentes para un mismo entorno. No deben desplegarse juntos porque duplicarían VPC, recursos de datos, grupos de seguridad y registros ECR.

## Operación, validación y seguridad

- [Runbook local y preproducción](operations/local-runbook.md): arranque, comprobaciones, perfiles y recuperación.
- [Informe de validación local](operations/local-validation-report.md): evidencia de las comprobaciones realizadas.
- [Registro consolidado de implementación y entrega](operations/project-delivery-record.md): cronología, cambios funcionales, correcciones, evidencia de validación y estado Git.
- [Seguridad de configuración local](../README.md#seguridad-de-configuración): secretos de desarrollo, JWT, CORS y límites de exposición.
- [Seguridad y límites actuales](../README.md#seguridad-y-límites-actuales): sesiones, API keys, Redis y perfil `local-production`.
- [Secretos y seguridad AWS](deployment/cloudformation-phased-plan.md#secretos): Secrets Manager, roles IAM, subnets privadas y límites de la propuesta.

Reglas operativas principales:

1. No subir `backend/.env`, secretos reales, API keys ni contraseñas productivas.
2. Mantener RDS, Redis, tareas ECS y secretos en subnets privadas; sólo el ALB y los componentes de borde deben recibir tráfico público.
3. Cambiar todos los valores de ejemplo antes de cualquier despliegue.
4. Revisar costes, dominio, certificados, disponibilidad y backups antes de promover la arquitectura a producción.
5. Ejecutar las validaciones offline disponibles antes de solicitar un despliegue AWS.

## Estado documental y alcance

- **Validado localmente:** desarrollo local, contratos principales, reglas de análisis, persistencia de alertas, workers Redis, 23 templates YAML, matriz JSON de parámetros, sintaxis PowerShell, paridad de parámetros, referencias cross-stack y formato Git.
- **MVP AWS staging validado:** cuenta `952763303883`, región `us-east-1`, ECS backend/worker 1/1, ALB HTTP, S3 Website, Amplify Hosting, Swagger/OpenAPI, CORS S3, registro/login/me y publicación final del frontend. Ver [MVP AWS staging](deployment/mvp-staging.md).
- **Resultados locales:** frontend 9/9; smoke API local y backend histórico registrados en [project-delivery-record.md](operations/project-delivery-record.md). La suite backend no se ejecutó en la última sesión porque `pytest` no estaba instalado en el host.
- **Preparado pero no habilitado:** producción HTTPS, dominio, ACM, CloudFront operativo, Bedrock autorizado, Knowledge Base ingerida y workers de IA/notificaciones activos.
- **Bloqueos del MVP:** CloudFront requiere verificación de cuenta; Bedrock devuelve `NOT_AUTHORIZED`; Amplify HTTPS no puede autenticarse contra el ALB HTTP.
- **Historial de base:** la preparación AWS parte del commit publicado `6fa93a3`; el estado actual debe verificarse con `git status --short --branch` y el [registro de MVP staging](deployment/mvp-staging.md).
- **Fuera del alcance inicial:** SQS gestionado, WAF, NAT Gateway, Multi-AZ completo, réplicas Redis y autoscaling avanzado.

## Convenciones de lectura

- Los archivos bajo `docs/` explican decisiones y procedimientos.
- Los templates bajo `infra/cloudformation/` son infraestructura declarativa; no contienen credenciales reales.
- La palabra **opcional** identifica una fase que requiere una decisión adicional o un dato externo, como un dominio.
- La documentación AWS no sustituye una revisión de seguridad, costes y operación antes de producción.

[Volver al README principal](../README.md)

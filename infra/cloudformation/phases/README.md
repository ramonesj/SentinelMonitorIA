# CloudFormation por fases

Los templates de este directorio son una alternativa modular a `../sentinel-monitoria-foundation.yaml`. Ejecutar sólo una estrategia por ambiente: foundation monolítica **o** fases modulares.

## Orden

```text
00-vpc-network
01-nat-instance
02-security-groups
03-iam
04-ecr
05-rds
06-redis
07-application-secrets
08-cloudwatch
09-alb
10-ecs-cluster
11-ecs-backend
12-ecs-worker
13-frontend-s3
14-cloudfront
15-route53-hosted-zone
16-acm-certificates
17-alb-https
18-route53-records
19-ai-platform
20-notification-platform
21-ecs-ai-worker
22-ecs-notification-worker
```

Cada stack exporta valores con el patrón `${ProjectName}-${EnvironmentName}-<OutputName>`. Los consumidores usan `Fn::ImportValue`; por eso los stacks deben permanecer en la misma cuenta y región.

## Capacidades IA y alertas

Las fases `19`–`22` añaden la ruta asíncrona de inteligencia sin alterar la ingesta:

- **19:** bucket S3 privado para archivo/contexto, logs del AI worker y rol IAM para Bedrock/Knowledge Base.
- **20:** secreto de canales, SNS opcional, rol IAM y logs del notification worker.
- **21:** servicio ECS ARM64 `python -m src.workers.ai_analysis_worker`; reglas locales por defecto y Bedrock opcional.
- **22:** servicio ECS ARM64 `python -m src.workers.notification_worker`; entregas idempotentes por log, email, webhook, Slack, Discord o Teams.

La fase 19 no crea automáticamente OpenSearch ni un Bedrock Knowledge Base porque ambos requieren elegir vector store, índice, modelo de embeddings, retención y presupuesto. El worker acepta `BedrockKnowledgeBaseId` cuando ya existe uno autorizado y el adapter local usa el contexto del batch. Las acciones automáticas permanecen desactivadas (`AI_ENABLE_ACTIONS=false`).

## Valores base

- Región: `us-east-1`.
- Ambiente: `staging`.
- DeploymentDay: `2026-07-23`.
- VPC: `10.42.0.0/16`.
- Públicas: `10.42.1.0/24`, `10.42.2.0/24`.
- Privadas: `10.42.11.0/24`, `10.42.12.0/24`.
- Backend: TCP 8000, health `/health`.
- Worker: `python -m src.workers.telemetry_worker`.
- NAT: `t4g.micro` ARM64 para staging.

La fase 14 puede usar el dominio predeterminado de CloudFront sin hosted zone ni dominio propio; enruta el frontend, la API, health, metrics y WebSocket al ALB. Una `AWS::CloudFront::Function` reescribe únicamente las rutas SPA sin extensión hacia `/index.html` y no convierte errores de API en respuestas `200` HTML. Las fases de dominio (`15`–`18`) son opcionales para un hostname propio y certificados ACM. CloudFront requiere que el certificado ACM esté en `us-east-1` sólo cuando se habilita un dominio custom.

- ElastiCache Redis mantiene `TransitEncryptionEnabled=true`.
- ECS envía `REDIS_TLS=true` y el backend usa `rediss://` con verificación del certificado.
- Los entornos Compose locales mantienen `REDIS_TLS=false` porque Redis local no usa TLS.
- RDS se migra mediante una tarea ECS one-off con `alembic upgrade head` antes de activar backend y worker.

## Herramientas operativas AWS

Desde la raíz, después de configurar credenciales AWS de forma segura:

```powershell
.\scripts\aws-preflight.ps1
.\scripts\validate-cloudformation.ps1
.\scripts\deploy-cloudformation-phases.ps1
.\scripts\build-push-ecr.ps1 -ImageTag v0.1.0
.\scripts\run-aws-migration.ps1
.\scripts\publish-frontend.ps1
```

Los scripts no contienen access keys ni secretos. El stack name usa el prefijo `sentinel-monitoria-` para que los roles generados por CloudFormation coincidan con la restricción de `iam:PassRole`. `aws-preflight.ps1` espera inicialmente la cuenta `952763303883` y el usuario `arn:aws:iam::952763303883:user/ramonesj`; usar `-AllowDifferentPrincipal` sólo si se cambia deliberadamente al rol de despliegue.

No hay credenciales en estos archivos. Los secretos de datos y aplicación se generan en Secrets Manager en las fases correspondientes.

# CloudFormation modular por fases

Esta es la ruta modular para desplegar SentinelMonitorIA en `us-east-1` sin una plantilla monolítica. Cada archivo de `infra/cloudformation/phases/` es un stack independiente. Los stacks se conectan mediante exports/imports de CloudFormation con el prefijo:

```text
${ProjectName}-${EnvironmentName}-<OutputName>
```

La foundation existente (`sentinel-monitoria-foundation.yaml`) se conserva como referencia y no debe desplegarse junto con estas fases: ambos diseños crearían recursos duplicados.

## Orden de fases

| Fase | Archivo | Servicio/alcance | Dependencias |
|---:|---|---|---|
| 00 | `00-vpc-network.yaml` | VPC, IGW, subnets, route tables y asociaciones | Ninguna |
| 01 | `01-nat-instance.yaml` | NAT instance ARM64, EIP, IAM de NAT y rutas privadas | 00 |
| 02 | `02-security-groups.yaml` | ALB, backend, PostgreSQL y Redis SG | 00 |
| 03 | `03-iam.yaml` | ECS execution role y task roles de backend/worker | Ninguna; se usa desde 11/12 |
| 04 | `04-ecr.yaml` | Repositorios ECR inmutables para backend y worker | Ninguna |
| 05 | `05-rds.yaml` | Secret generado, subnet group y RDS PostgreSQL privado | 00, 02 |
| 06 | `06-redis.yaml` | Secret generado, subnet group y ElastiCache Redis privado | 00, 02 |
| 07 | `07-application-secrets.yaml` | Secretos generados para `SECRET_KEY` y `JWT_SECRET_KEY` | Ninguna |
| 08 | `08-cloudwatch.yaml` | Log groups para backend, worker y ALB | Ninguna |
| 09 | `09-alb.yaml` | ALB público, target group HTTP:8000 y listener HTTP:80 | 00, 02 |
| 10 | `10-ecs-cluster.yaml` | ECS cluster Fargate y Container Insights | Ninguna |
| 11 | `11-ecs-backend.yaml` | Task definition y ECS service backend | 00, 02, 03, 04, 05, 06, 07, 08, 09, 10 |
| 12 | `12-ecs-worker.yaml` | Task definition y ECS service worker | 00, 02, 03, 04, 05, 06, 07, 08, 10 |
| 13 | `13-frontend-s3.yaml` | Bucket privado para `frontend/dist` | Ninguna |
| 14 | `14-cloudfront.yaml` | OAC y distribución CloudFront para el bucket | 13; ACM opcional |
| 15 | `15-route53-hosted-zone.yaml` | Hosted Zone pública | Dominio propio |
| 16 | `16-acm-certificates.yaml` | Certificados ACM para API y frontend | 15; región us-east-1 |
| 17 | `17-alb-https.yaml` | Listener HTTPS y redirect HTTP→HTTPS opcional | 09, 16 |
| 18 | `18-route53-records.yaml` | Alias DNS hacia ALB y CloudFront | 14, 15, 17 |
| 19 | `19-ai-platform.yaml` | S3 de contexto/archivo, logs y rol IAM para Bedrock | 03, 08 |
| 20 | `20-notification-platform.yaml` | Secreto de canales, SNS opcional, logs y rol IAM | 03, 08 |
| 21 | `21-ecs-ai-worker.yaml` | Worker ECS de reglas, análisis y explicaciones Bedrock | 04, 05, 06, 07, 08, 10, 19 |
| 22 | `22-ecs-notification-worker.yaml` | Worker ECS de email/webhooks/chat y entregas idempotentes | 04, 05, 06, 07, 08, 10, 20 |

Las fases 15–18 son opcionales hasta disponer de un dominio controlado por el equipo. Las fases 14 y 18 aceptan modo sin dominio para pruebas, usando el dominio DNS generado por CloudFront y el DNS del ALB.

## Contrato de red

La fase 00 crea:

- VPC: `10.42.0.0/16`.
- Públicas: `10.42.1.0/24` (`us-east-1a`) y `10.42.2.0/24` (`us-east-1b`).
- Privadas: `10.42.11.0/24` (`us-east-1a`) y `10.42.12.0/24` (`us-east-1b`).
- Ruta pública `0.0.0.0/0` hacia el Internet Gateway.
- Route tables privadas sin ruta externa hasta completar la fase 01.

La fase 01 coloca una NAT instance `t4g.micro` ARM64 en la primera subnet pública, desactiva `SourceDestCheck`, configura EIP y añade `0.0.0.0/0 → NAT instance` a ambas route tables privadas. Producción debe evaluar NAT Gateway o redundancia por AZ.

## Contrato de aplicación

- Backend: imagen ECR indicada por `BackendImageTag`, puerto 8000, health check `/health`, target type `ip`.
- Worker: misma imagen ECR, comando `python -m src.workers.telemetry_worker`, sin listener público.
- Frontend: `npm run build` produce `frontend/dist`; el Dockerfile actual es de desarrollo Vite en puerto 3000 y no se usa para la distribución S3/CloudFront.
- Backend ECS usa subnets privadas y `AssignPublicIp: DISABLED`.
- ALB es público y sólo el security group del ALB entra al backend en TCP 8000.
- RDS y Redis sólo aceptan tráfico del security group del backend.

## Contrato de inteligencia y notificaciones

La aplicación publica el batch en la cola `ai_analysis` sólo después de que el worker de telemetry confirme la persistencia en PostgreSQL. El worker de análisis:

- ejecuta reglas determinísticas de CPU, memoria, logs y eventos;
- puede usar Ollama local o Bedrock Converse para explicar señales;
- puede recuperar contexto de un Bedrock Knowledge Base existente mediante `BedrockKnowledgeBaseId`;
- crea `AIAnalysis` y `Alert` con una clave de deduplicación por organización/batch;
- publica una entrega por canal en `notifications` sin ejecutar acciones operativas.

El notification worker persiste cada intento en `NotificationDelivery`, aplica reintentos/DLQ de Redis Streams y soporta `log`, `email`, `webhook`, `slack`, `discord` y `teams`. El endpoint autenticado `/api/v1/alerts` permite consultar y reconocer alertas; `/api/v1/alerts/ws` ofrece actualizaciones por WebSocket mediante polling seguro de la base de datos.

## Vector store y RAG

El contexto local se limita al batch actual para no introducir un servicio pesado en Docker Compose. En AWS, S3 se prepara en la fase 19 y el código puede consultar un Knowledge Base de Bedrock existente. OpenSearch/pgvector, embeddings, sincronización de documentos y retención deben elegirse como una fase posterior explícita; no se crean automáticamente para evitar costes y una configuración de índice incompleta.

## Secretos

Las fases 05 y 06 generan secretos de Secrets Manager para las credenciales de RDS y Redis, respectivamente. La contraseña nunca se escribe en un parámetro versionado; RDS/Redis consumen referencias dinámicas y ECS recibe referencias a claves JSON del secreto.

La fase 07 genera `SECRET_KEY` y `JWT_SECRET_KEY`. El execution role de ECS sólo permite leer secretos bajo el prefijo de la aplicación. No se deben sustituir estos recursos por valores en `.env` o `parameters.example.json`.

## Parámetros comunes

Todos los stacks etiquetables reciben:

- `Project`: `ProjectName`.
- `Environment`: `EnvironmentName`.
- `DeploymentDay`: `2026-07-23`.
- `ManagedBy`: `CloudFormation`.
- `CostCenter`: `${ProjectName}-${EnvironmentName}`.

Los archivos no tienen credenciales AWS. Los únicos valores sensibles se generan dentro de Secrets Manager durante un despliegue real.

## Preparación de imágenes

Antes de las fases 11 y 12:

1. Crear ECR con la fase 04.
2. Construir imágenes para `linux/arm64`, porque los task definitions usan ARM64.
3. Publicar tags inmutables en ECR.
4. Pasar el tag publicado como `BackendImageTag` y `WorkerImageTag`.
5. Ejecutar migraciones Alembic de forma controlada antes de marcar el backend como listo.

El backend y el worker comparten `backend/Dockerfile`; sólo cambia el comando del contenedor worker.

## Validación y ejecución futura

La preparación actual es offline. Para ejecutar después:

```powershell
$region = 'us-east-1'
$base = 'infra/cloudformation/phases'

aws cloudformation validate-template --region $region --template-body file://$base/00-vpc-network.yaml
```

Validar cada archivo antes de crear Change Sets. No ejecutar las fases 11–12 hasta confirmar imágenes, secretos, RDS, Redis, target group y logs.

## Rollback y limpieza

- Cada stack puede actualizarse o eliminarse de forma independiente respetando sus exports.
- Eliminar primero consumidores de exports: DNS/HTTPS, CloudFront, ECS, ALB y luego datos/red.
- RDS, Redis, secretos y ECR tienen retención de datos/repositorios definida en sus templates; borrar el stack no garantiza coste cero.
- Vaciar S3/ECR, eliminar snapshots/logs innecesarios y liberar EIP explícitamente.
- No desplegar la foundation monolítica y las fases modulares en la misma cuenta/ambiente.

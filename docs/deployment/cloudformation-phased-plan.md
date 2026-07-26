# CloudFormation modular por fases

**Última actualización:** 23 de julio de 2026, 21:59 (UTC-05:00)

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
| 14 | `14-cloudfront.yaml` | OAC, frontend S3, origen ALB para API/health/WebSocket y dominio CloudFront predeterminado o custom | 09, 13; ACM opcional |
| 15 | `15-route53-hosted-zone.yaml` | Hosted Zone pública | Dominio propio |
| 16 | `16-acm-certificates.yaml` | Certificados ACM para API y frontend | 15; región us-east-1 |
| 17 | `17-alb-https.yaml` | Listener HTTPS y redirect HTTP→HTTPS opcional | 09, 16 |
| 18 | `18-route53-records.yaml` | Alias DNS hacia ALB y CloudFront | 14, 15, 17 |
| 19 | `19-ai-platform.yaml` | S3 de contexto/archivo, logs y rol IAM para Bedrock | 03, 08 |
| 20 | `20-notification-platform.yaml` | Secreto de canales, SNS opcional, logs y rol IAM | 03, 08 |
| 21 | `21-ecs-ai-worker.yaml` | Worker ECS de reglas, análisis y explicaciones Bedrock | 04, 05, 06, 07, 08, 10, 19 |
| 22 | `22-ecs-notification-worker.yaml` | Worker ECS de email/webhooks/chat y entregas idempotentes | 04, 05, 06, 07, 08, 10, 20 |

La fase 14 puede desplegarse sin dominio propio ni hosted zone: usa el DNS predeterminado de CloudFront, sirve el frontend desde S3 y enruta `/api/*`, `/health`, `/metrics` y WebSocket hacia el ALB. Las fases 15–18 sólo son necesarias para un hostname propio, certificados ACM o registros DNS administrados en Route 53.

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
- CloudFront: el dominio predeterminado es el punto público recomendado sin dominio propio; el behavior raíz usa S3 y una CloudFront Function reescribe rutas SPA sin extensión hacia `/index.html`; los behaviors `/api/*`, `/health*` y `/metrics*` usan el ALB sin cache. El behavior `/api/*` conserva `Authorization`, CORS y headers de WebSocket, y los errores de API no se convierten en `index.html`.
- Para publicar el frontend contra el mismo enlace, obtener primero el output `CloudFrontDomainName`, construir con `VITE_API_BASE_URL=https://<CloudFrontDomainName>` y cargar `frontend/dist` en el bucket S3. Configurar `CorsOrigins` del backend con ese mismo origen.
- Backend ECS usa subnets privadas y `AssignPublicIp: DISABLED`; recibe `REDIS_TLS=true` en AWS y conecta con `rediss://` a ElastiCache.
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

## Preparación de imágenes y runtime

Antes de activar las fases 11, 12, 21 y 22:

1. Crear ECR con la fase 04.
2. Construir las imágenes para `linux/arm64`, porque todas las task definitions ECS usan ARM64.
3. Publicar tags inmutables en ECR con `.\scripts\build-push-ecr.ps1`.
4. Pasar el mismo tag publicado como `BackendImageTag` y `WorkerImageTag`; la imagen worker compartida sirve para telemetría, análisis IA y notificaciones.
5. Mantener `RedisTls=true` en ECS: la fase 06 usa `TransitEncryptionEnabled=true` y los workers utilizan `rediss://` con verificación de certificado.
6. Mantener `AiProvider=rules` y `NotificationChannels=log` durante la primera prueba para no activar Bedrock ni destinos externos.
7. Ejecutar Alembic como una tarea ECS one-off antes de activar backend, telemetry worker, AI worker y notification worker. Las migraciones `0004` y `0005` crean las tablas requeridas por IA y alertas.

El backend y los tres workers comparten `backend/Dockerfile`; sólo cambia el comando del contenedor. `backend/alembic.ini` es parte del runtime y no debe quedar excluido por `.gitignore`.

## Flujo recomendado sin dominio propio

La cuenta de despliegue debe validarse primero. El preflight espera la cuenta `952763303883` y el usuario `arn:aws:iam::952763303883:user/ramonesj`, pero nunca guarda ni imprime credenciales:

```powershell
.\scripts\aws-preflight.ps1
.\scripts\validate-cloudformation.ps1 -IncludeAiNotifications
```

Para revisar un Change Set sin ejecutarlo, usar la fase individual con `-NoExecuteChangeSet`. La secuencia segura recomendada es:

```powershell
# Red, seguridad, IAM, ECR, datos, secretos, logs, ALB y cluster.
# Se dejan fuera los servicios, frontend y CloudFront para preparar el runtime.
.\scripts\deploy-cloudformation-phases.ps1 `
  -SkipPhase 11-ecs-backend,12-ecs-worker,13-frontend-s3,14-cloudfront

# Crear la plataforma opcional de IA y notificaciones.
.\scripts\deploy-cloudformation-phases.ps1 -Phase 19-ai-platform
.\scripts\deploy-cloudformation-phases.ps1 -Phase 20-notification-platform

# Publicar ambas imágenes ARM64 con un tag inmutable.
.\scripts\build-push-ecr.ps1 -ImageTag v0.1.0

# Crear task definitions y los cuatro servicios detenidos para poder migrar RDS.
.\scripts\deploy-cloudformation-phases.ps1 -Phase 11-ecs-backend -StopServices
.\scripts\deploy-cloudformation-phases.ps1 -Phase 12-ecs-worker -StopServices
.\scripts\deploy-cloudformation-phases.ps1 -Phase 21-ecs-ai-worker -StopServices
.\scripts\deploy-cloudformation-phases.ps1 -Phase 22-ecs-notification-worker -StopServices

# Ejecutar la migración contra RDS usando la red privada y los secretos ECS.
.\scripts\run-aws-migration.ps1

# Activar backend y workers después de confirmar Alembic.
.\scripts\deploy-cloudformation-phases.ps1 -Phase 11-ecs-backend
.\scripts\deploy-cloudformation-phases.ps1 -Phase 12-ecs-worker
.\scripts\deploy-cloudformation-phases.ps1 -Phase 21-ecs-ai-worker
.\scripts\deploy-cloudformation-phases.ps1 -Phase 22-ecs-notification-worker

# Crear el bucket y la distribución CloudFront.
.\scripts\deploy-cloudformation-phases.ps1 -Phase 13-frontend-s3
.\scripts\deploy-cloudformation-phases.ps1 -Phase 14-cloudfront
```

`-IncludeAiNotifications` amplía el recorrido normal `00-14` con `19-22`, pero no sustituye la migración ni la configuración de secretos. Para una primera puesta en marcha es más seguro usar las fases opcionales individualmente con `-StopServices`, como en la secuencia anterior. Bedrock se mantiene desactivado con `AiProvider=rules` y los destinos externos con `NotificationChannels=log` hasta confirmar costes, permisos y conectividad.

La fase 14 usa una CloudFront Function de viewer request para reescribir rutas SPA sin extensión a `/index.html`. No usa `CustomErrorResponses` globales, por lo que los errores `401`, `403` y `404` de la API conservan su respuesta original.

Después de obtener el output `CloudFrontDomainName`, actualizar CORS y publicar el frontend:

```powershell
$cloudFrontDomain = 'CLOUDFRONT_DOMAIN'
.\scripts\deploy-cloudformation-phases.ps1 `
  -Phase 11-ecs-backend `
  -AdditionalParameterOverride "CorsOrigins=https://$cloudFrontDomain"
.\scripts\publish-frontend.ps1 -CloudFrontDomainName $cloudFrontDomain
```

`publish-frontend.ps1` compila con `VITE_API_BASE_URL=https://<CloudFrontDomainName>`, sincroniza `frontend/dist` al bucket S3 exportado y crea una invalidación `/*` en CloudFront. El endpoint público final es `https://<CloudFrontDomainName>`.

En el modo sin dominio, CloudFront termina HTTPS para el navegador y el origen ALB usa `http-only` por defecto. Para producción con cifrado también entre CloudFront y ALB, activar la fase 17 con un certificado ACM para un dominio propio y cambiar `ApiOriginProtocolPolicy` a `https-only`.

## Validación y ejecución futura

La preparación local puede comprobarse con:

```powershell
python -c "import yaml; from pathlib import Path; paths=sorted(Path('infra/cloudformation/phases').glob('*.yaml')); [list(yaml.parse(p.read_text(encoding='utf-8'))) for p in paths]; print(f'YAML OK: {len(paths)} templates')"
python -c "import json; json.load(open('infra/cloudformation/phases/parameters.example.json', encoding='utf-8')); print('Parameters JSON OK')"
.\scripts\validate-cloudformation.ps1
```

`validate-cloudformation.ps1`, `aws-preflight.ps1` y los scripts de publicación realizan llamadas AWS sólo cuando se ejecutan explícitamente con credenciales configuradas. Usa `validate-cloudformation.ps1 -IncludeAiNotifications` para incluir 19–22 en la validación. No ejecutar las fases 11, 12, 21 ni 22 con `DesiredCount=1` hasta confirmar imágenes ARM64, secretos, RDS, Redis TLS, target group, logs y migración completada.

## Rollback y limpieza

- Cada stack puede actualizarse o eliminarse de forma independiente respetando sus exports.
- Eliminar primero consumidores de exports: DNS/HTTPS, CloudFront, ECS, ALB y luego datos/red.
- RDS, Redis, secretos y ECR tienen retención de datos/repositorios definida en sus templates; borrar el stack no garantiza coste cero.
- Vaciar S3/ECR, eliminar snapshots/logs innecesarios y liberar EIP explícitamente.
- No desplegar la foundation monolítica y las fases modulares en la misma cuenta/ambiente.

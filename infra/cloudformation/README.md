# CloudFormation de SentinelMonitorIA

Esta carpeta contiene dos estrategias offline:

- `sentinel-monitoria-foundation.yaml`: plantilla monolítica histórica para una foundation completa.
- `phases/`: estrategia modular recomendada, con un stack CloudFormation por fase/servicio.

No se deben desplegar las dos estrategias en el mismo ambiente, porque ambas crearían VPC, datos, ECR y otros recursos duplicados.

## Ruta modular recomendada

Los templates se ejecutan en este orden:

```text
00-vpc-network.yaml
01-nat-instance.yaml
02-security-groups.yaml
03-iam.yaml
04-ecr.yaml
05-rds.yaml
06-redis.yaml
07-application-secrets.yaml
08-cloudwatch.yaml
09-alb.yaml
10-ecs-cluster.yaml
11-ecs-backend.yaml
12-ecs-worker.yaml
13-frontend-s3.yaml
14-cloudfront.yaml
15-route53-hosted-zone.yaml
16-acm-certificates.yaml
17-alb-https.yaml
18-route53-records.yaml
19-ai-platform.yaml
20-notification-platform.yaml
21-ecs-ai-worker.yaml
22-ecs-notification-worker.yaml
```

Detalles de dependencias, exports/imports, puertos, health checks, imágenes y limpieza están en `docs/deployment/cloudformation-phased-plan.md`. La matriz no secreta de parámetros está en `phases/parameters.example.json`.

## Recursos por fase

- **00:** VPC `10.42.0.0/16`, subnets públicas/privadas, IGW y route tables.
- **01:** NAT instance `t4g.micro` ARM64, EIP, forwarding, IAM de SSM/CloudWatch y rutas privadas.
- **02:** ALB SG, backend SG, RDS SG y Redis SG.
- **03:** ECS execution role y task roles separados.
- **04:** ECR backend/worker, scan on push, tags inmutables y lifecycle de imágenes.
- **05:** Secrets Manager de PostgreSQL, subnet group y RDS privado.
- **06:** Secrets Manager de Redis, subnet group y ElastiCache privado.
- **07:** `SECRET_KEY` y `JWT_SECRET_KEY` generados en Secrets Manager.
- **08:** Log groups de backend y worker con retención configurable.
- **09:** ALB público, target group TCP 8000/HTTP y health `/health`.
- **10:** ECS Fargate cluster con Container Insights.
- **11:** Backend ARM64 en Fargate, secretos, logs, RDS/Redis y ALB.
- **12:** Worker ARM64 en Fargate con `python -m src.workers.telemetry_worker`.
- **13:** Bucket S3 privado para `frontend/dist`.
- **14:** CloudFront + Origin Access Control para S3.
- **15:** Hosted Zone pública, sólo con dominio controlado.
- **16:** Certificados ACM DNS-validated; debe ejecutarse en `us-east-1`.
- **17:** HTTPS ALB y redirect HTTP→HTTPS opcional.
- **18:** Alias Route 53 para API y frontend, opcional.
- **19:** Archivo S3 privado, bucket e índice S3 Vectors, Knowledge Base Bedrock con Titan Embeddings V2, Data Source S3, logs y roles IAM.
- **20:** Secreto de canales, SNS opcional, logs y rol IAM del notification worker.
- **21:** Worker ECS ARM64 de análisis con Nova Lite, recuperación desde la Knowledge Base administrada y creación de alertas.
- **22:** Worker ECS ARM64 de notificaciones con entregas idempotentes y canales configurables.

La fase 19 crea el vector store y la Knowledge Base dentro del mismo stack. El Data Source sólo incluye `knowledge-base/` del bucket S3 de archivo; publique allí documentos redactados con `scripts/publish-bedrock-knowledge-base.ps1`. La fase 21 consume el ID mediante el export `AiKnowledgeBaseId`, mantiene `AI_ENABLE_ACTIONS=false` y deja `NotificationChannels=log` como valor inicial.

## Recursos por fase

Desde la raíz del repositorio:

```powershell
python -c "import yaml; from pathlib import Path; [list(yaml.parse(p.read_text(encoding='utf-8'))) for p in Path('infra/cloudformation/phases').glob('*.yaml')]; print('YAML OK')"
python -c "import json; json.load(open('infra/cloudformation/phases/parameters.example.json', encoding='utf-8')); print('Parameters JSON OK')"
git diff --check
```

Con una cuenta AWS y después de revisar los Change Sets:

```powershell
aws cloudformation validate-template --region us-east-1 --template-body file://infra/cloudformation/phases/00-vpc-network.yaml
```

La validación contra AWS, Change Sets y despliegues no forman parte de esta preparación. No hay credenciales ni secretos reales en los ejemplos.

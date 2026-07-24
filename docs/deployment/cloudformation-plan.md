# Plan de infraestructura AWS sin despliegue

Este documento define la preparación que puede hacerse antes de disponer de una cuenta AWS. No crea recursos ni contiene IDs, credenciales o secretos reales.

## Capas propuestas

1. **Foundation**: VPC, subnets públicas/privadas, tablas de rutas, security groups y outputs de red.
2. **Data**: RDS PostgreSQL privado, subnet group, ElastiCache Redis privado, backups y parámetros.
3. **Application**: ECR, ECS/Fargate, task definitions, backend, worker, ALB, health checks y logs.
4. **Edge**: Route 53, ACM, HTTPS, WAF y políticas CORS.
5. **Operations**: CloudWatch logs, alarmas, dashboards, backups y notificaciones.

La plantilla `infra/cloudformation/sentinel-monitoria-foundation.yaml` es una base offline para las capas de red/datos y repositorios ECR. ECS, DNS y certificados deben añadirse después de decidir cuenta, región, dominio, estrategia de costes y límites de seguridad.

## Parámetros que deben decidirse con la cuenta AWS

- Región y nombre de ambientes: `staging` y `production`.
- CIDR de VPC y subnets.
- Tipo y tamaño de RDS/ElastiCache.
- Política de backups, retención y recuperación.
- Repositorio ECR y estrategia de tags.
- Dominio y certificados ACM.
- Tamaño mínimo/máximo de ECS y estrategia de despliegue.
- Roles IAM separados para tareas backend y worker.
- Secretos gestionados en Secrets Manager, nunca en parámetros versionados.

## Validación offline

Con AWS CLI configurado, la validación final será:

```powershell
aws cloudformation validate-template --template-body file://infra/cloudformation/sentinel-monitoria-foundation.yaml
```

Sin cuenta AWS puede hacerse validación sintáctica YAML y revisión de parámetros. `validate-template`, creación de cambios, costes, cuotas y conectividad sólo pueden verificarse con una cuenta.

## Orden de despliegue futuro

1. Foundation.
2. Data y secretos.
3. ECR e imágenes.
4. ECS backend/worker y ALB.
5. Migración Alembic controlada.
6. Frontend y DNS/HTTPS.
7. Alarmas, backups y prueba de rollback.

## Reglas de seguridad

- RDS y Redis no deben ser públicos.
- Sólo el security group del backend accede a RDS/Redis.
- El ALB es el único componente público de la API.
- Las tareas ECS usan roles IAM mínimos.
- Las contraseñas y claves JWT se obtienen de Secrets Manager.
- La eliminación accidental de datos debe estar protegida con `DeletionPolicy: Retain` y backups.

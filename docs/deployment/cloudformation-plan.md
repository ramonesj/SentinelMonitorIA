# Plan de infraestructura AWS sin despliegue

Este documento define una preparación reproducible para SentinelMonitorIA en **`us-east-1` (Norte de Virginia)**. Los archivos son offline: no crean recursos, no contienen credenciales y no deben ejecutarse contra una cuenta sin una revisión previa.

## Alcance de la foundation

La plantilla `infra/cloudformation/sentinel-monitoria-foundation.yaml` cubre:

1. VPC y DNS interno.
2. Dos subnets públicas y dos privadas distribuidas en dos AZ.
3. Internet Gateway, una tabla de rutas pública y dos tablas privadas.
4. NAT instance ARM64 para staging, Elastic IP, security group, IAM instance profile y CloudWatch/SSM.
5. RDS PostgreSQL privado y ElastiCache Redis privado.
6. Security groups de backend, base de datos, Redis y NAT.
7. Dos repositorios ECR para backend y worker.
8. Outputs de CIDR, subnets, tablas de rutas, NAT y endpoints de datos.

ECS/Fargate, ALB, frontend S3/CloudFront, Route 53, ACM, WAF, OpenSearch y alarmas avanzadas son capas posteriores. La foundation no declara esos recursos.

## Parámetros reproducibles

- `ProjectName`: `SentinelMonitorIA`.
- `EnvironmentName`: `staging` o `production`.
- `DeploymentDay`: `2026-07-23`, formato ISO `YYYY-MM-DD`.
- `VpcCidr`: `10.42.0.0/16`.
- `PublicSubnet1Cidr`: `10.42.1.0/24` en `us-east-1a`.
- `PublicSubnet2Cidr`: `10.42.2.0/24` en `us-east-1b`.
- `PrivateSubnet1Cidr`: `10.42.11.0/24` en `us-east-1a`.
- `PrivateSubnet2Cidr`: `10.42.12.0/24` en `us-east-1b`.
- `NatInstanceType`: `t4g.micro` por defecto para staging.
- `NatAmiParameter`: parámetro público de SSM de Amazon Linux 2023 ARM64.
- `NatRootVolumeSize`: 8 GiB gp3 cifrados.
- RDS: `db.t4g.micro`, 20 GiB gp3, una AZ, retención de backups configurable.
- Redis: `cache.t4g.micro`, un nodo, sin failover automático.

`AvailabilityZone1` y `AvailabilityZone2` se mantienen como parámetros para que el mismo archivo pueda validarse en otra cuenta sin hardcodear la selección de AZ. La ejecución prevista para esta estimación es exclusivamente `us-east-1`.

## Red y enrutamiento

| Recurso | CIDR/objetivo | AZ | Tabla de rutas |
|---|---|---|---|
| VPC | `10.42.0.0/16` | Regional | — |
| PublicSubnet1 | `10.42.1.0/24` | `us-east-1a` | `PublicRouteTable` |
| PublicSubnet2 | `10.42.2.0/24` | `us-east-1b` | `PublicRouteTable` |
| PrivateSubnet1 | `10.42.11.0/24` | `us-east-1a` | `PrivateRouteTable1` |
| PrivateSubnet2 | `10.42.12.0/24` | `us-east-1b` | `PrivateRouteTable2` |

Rutas declaradas:

- `PublicRouteTable`: `0.0.0.0/0 → InternetGateway`.
- `PrivateRouteTable1`: `0.0.0.0/0 → NatInstance`.
- `PrivateRouteTable2`: `0.0.0.0/0 → NatInstance`.
- Las subnets privadas no asignan IPv4 pública al lanzamiento.
- La NAT se coloca en `PublicSubnet1`, con Elastic IP y `SourceDestCheck: false`.

La NAT permite que RDS, Redis o tareas privadas alcancen servicios externos para actualizaciones y operaciones. El tráfico de entrada desde Internet no se habilita por la NAT; el security group sólo acepta forwarding desde los CIDR privados configurados.

## Etiquetas comunes

Todos los recursos que admiten tags reciben como mínimo:

| Key | Valor |
|---|---|
| `Project` | `!Ref ProjectName` |
| `Environment` | `!Ref EnvironmentName` |
| `DeploymentDay` | `!Ref DeploymentDay` |
| `ManagedBy` | `CloudFormation` |
| `CostCenter` | `${ProjectName}-${EnvironmentName}` |

Además, cada recurso conserva un `Name` estable y, cuando aplica, una etiqueta `Tier`, `Component` o `Purpose`. Las rutas, asociaciones y attachments que no soportan tags quedan identificados por sus nombres lógicos y outputs.

## NAT instance y bootstrap

La instancia usa el parámetro de SSM:

```text
/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64
```

El UserData se redujo para que sea apropiado para Amazon Linux 2023 ARM64:

- `set -Eeuo pipefail` y sin `set -x`, evitando exponer tokens IMDS en logs.
- No usa `jq`, `wget`, `lsof`, `netstat` ni `at` sin instalar esos paquetes.
- Instala sólo `iptables-services`, `iproute` y `curl` además del agente requerido.
- Descarga el RPM de CloudWatch a un archivo local y ejecuta `rpm` sobre ese archivo.
- Activa IPv4 forwarding, MASQUERADE y reglas explícitas de `FORWARD` con estados `NEW,ESTABLISHED,RELATED`.
- Persiste iptables y sólo crea el marcador `firstrun` al finalizar correctamente.
- No reinicia automáticamente la máquina ni modifica SELinux durante el primer bootstrap.

El IAM role incluye `AmazonSSMManagedInstanceCore` y `CloudWatchAgentServerPolicy`. Para producción se debe revisar el principio de mínimo privilegio y considerar VPC endpoints para SSM/CloudWatch.

## Datos y seguridad

- RDS y Redis son privados y sólo aceptan tráfico desde `BackendSecurityGroup`.
- La NAT acepta tráfico de forwarding desde los CIDR privados y tiene egress de salida.
- RDS y Redis usan cifrado y backups configurables.
- `DBPassword` y `RedisAuthToken` son parámetros `NoEcho`, pero siguen siendo secretos introducidos durante la operación; la solución de producción debe migrarlos a Secrets Manager.
- No se deben guardar valores reales en `parameters.example.json`, `.env.example` ni en el repositorio.
- La plantilla conserva RDS, Redis y ECR mediante `DeletionPolicy: Retain` y `UpdateReplacePolicy: Retain`. Esto protege datos, pero puede dejar recursos facturables después de borrar el stack.

## Validación offline

Desde la raíz del repositorio:

```powershell
cfn-lint -t infra/cloudformation/sentinel-monitoria-foundation.yaml
python -c "import yaml; yaml.safe_load(open('infra/cloudformation/sentinel-monitoria-foundation.yaml', encoding='utf-8')); print('YAML OK')"
git diff --check
```

Con una cuenta AWS disponible, la validación específica de CloudFormation sería:

```powershell
aws cloudformation validate-template --region us-east-1 --template-body file://infra/cloudformation/sentinel-monitoria-foundation.yaml
```

Ese último comando consulta AWS y no forma parte de esta preparación offline. Antes de una ejecución real también hay que comprobar disponibilidad de la AMI SSM, tipos de instancia, versión de PostgreSQL, cuotas, límites de IP y precios vigentes.

## Orden de despliegue futuro

1. Confirmar cuenta, región, presupuesto, AZ y valores de secretos.
2. Ejecutar un Change Set de la foundation.
3. Crear foundation y revisar outputs de VPC, CIDR, tablas, NAT, EIP y security groups.
4. Validar SSM/CloudWatch y conectividad de salida desde una instancia privada.
5. Confirmar RDS/Redis y migraciones Alembic controladas.
6. Crear ECR, publicar imágenes inmutables y configurar roles IAM separados.
7. Añadir ECS/Fargate, worker y ALB con health checks.
8. Añadir frontend, HTTPS, DNS, logs, alarmas y pruebas de rollback.

## Limpieza y rollback

- Usar Change Sets para cambios que puedan reemplazar RDS, Redis o la NAT.
- Antes de eliminar datos, crear snapshots y registrar los identificadores fuera del repositorio.
- Vaciar ECR/S3 antes de borrar repositorios/buckets.
- Eliminar explícitamente recursos retenidos después de borrar el stack si ya no son necesarios.
- Liberar la Elastic IP y revisar CloudWatch logs, EBS, snapshots y backups.
- Confirmar el resultado en Billing/Cost Explorer; `DeleteStack` no es evidencia de coste cero cuando existe `Retain`.

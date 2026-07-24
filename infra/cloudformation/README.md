# CloudFormation foundation

Esta carpeta contiene diseño IaC offline. No se ha desplegado ni validado contra una cuenta AWS.

## Contenido

- `sentinel-monitoria-foundation.yaml`: VPC, subnets privadas/públicas, security groups, RDS PostgreSQL, ElastiCache Redis y repositorios ECR.
- `parameters.example.json`: valores no secretos para revisión local; sustituir las Availability Zones por las disponibles en la región elegida.

La foundation deja las subnets privadas sin ruta de salida a Internet ni NAT Gateway para evitar costes implícitos y mantener RDS/Redis aislados. La capa ECS futura deberá añadir el egress necesario (por ejemplo, NAT gestionado) tras revisar costes y requisitos de imágenes/actualizaciones.

## Validación

```powershell
aws cloudformation validate-template --template-body file://infra/cloudformation/sentinel-monitoria-foundation.yaml
```

La plantilla requiere revisión de costes, CIDR, región, tamaños y políticas IAM antes de cualquier despliegue. Los secretos se modelan como parámetros `NoEcho` sólo para la base offline; el diseño de producción debe resolverlos desde Secrets Manager.

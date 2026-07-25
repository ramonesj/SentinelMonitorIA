# Estimación mensual AWS para SentinelMonitorIA

**Estado:** preparación offline; esta estimación no crea recursos ni representa una factura de AWS.

## Alcance y supuestos

| Concepto | Supuesto |
|---|---|
| Región | `us-east-1` — Norte de Virginia |
| Periodo | 730 horas/mes; para la prueba de 3 días se usan 72 horas |
| Ambiente | `staging`, una sola instalación, tráfico bajo |
| NAT | Una instancia `t4g.micro` ARM64 con Amazon Linux 2023 y una IPv4 pública |
| Datos | RDS PostgreSQL `db.t4g.micro`, 20 GiB gp3, una AZ; ElastiCache Redis `cache.t4g.micro`, un nodo |
| Aplicación | Un servicio ECS/Fargate para backend y uno para worker, más una tarea ARM64 para análisis IA y otra para notificaciones; todas pequeñas para staging |
| Entrada | Un Application Load Balancer; frontend estático en S3 + CloudFront con tráfico bajo |
| Repositorios | Dos repositorios ECR: backend y worker |
| No incluido | OpenSearch, Bedrock Knowledge Base, inferencia Bedrock, WAF, NAT Gateway, Multi-AZ, réplicas Redis, SQS, alarmas avanzadas y tráfico significativo |

La plantilla `infra/cloudformation/sentinel-monitoria-foundation.yaml` prepara la red, NAT, RDS, Redis y ECR. ECS/Fargate, ALB, S3, CloudFront, DNS y ACM pertenecen a capas posteriores. Las fases `19`–`22` incorporan archivo IA, Bedrock opcional, análisis asíncrono y notificaciones; no se despliegan con la foundation monolítica.

Los importes son rangos de planificación para `us-east-1`, no una cotización contractual. El precio final depende de la arquitectura exacta, transferencia, almacenamiento, logs, backups, promociones y cambios de precios. El objetivo siguiente cubre el cómputo de IA/notificaciones y sus servicios base, pero **no** incluye el consumo variable de inferencia Bedrock ni un vector store administrado.

## Presupuesto mensual de staging ARM64

Con 730 horas y tráfico bajo, el presupuesto recomendado para la solución completa es **USD 95–120/mes antes de Bedrock y del vector store**. Conviene reservar hasta **USD 125–150/mes** si se habilitan más logs, transferencia, tareas con mayor CPU/memoria o canales de correo. Bedrock se presupuesta por tokens y puede convertirse en la partida dominante si se analizan grandes volúmenes.

| Componente | Rango mensual orientativo | Parte aproximada de 72 h | Observaciones |
|---|---:|---:|---|
| NAT `t4g.micro` + IPv4 pública | USD 10–12 | USD 1.00–1.20 | La instancia evita el coste fijo de un NAT Gateway, pero requiere operación y no es HA. |
| RDS PostgreSQL `db.t4g.micro` + 20 GiB | USD 14–17 | USD 1.38–1.68 | Una AZ, almacenamiento gp3 y backups de staging. |
| ElastiCache Redis `cache.t4g.micro` | USD 12–15 | USD 1.18–1.48 | Un nodo, sin failover automático. |
| ECS/Fargate backend + worker | USD 13–18 | USD 1.28–1.78 | Dos tareas ARM64 pequeñas; subir CPU/memoria incrementa el coste. |
| ECS/Fargate AI worker | USD 10–16 | USD 0.99–1.58 | Una tarea ARM64 de referencia `0.5 vCPU / 1 GiB` para la fase 21; escala con `DesiredCount`. |
| ECS/Fargate notification worker | USD 5–9 | USD 0.49–0.89 | Una tarea ARM64 de referencia `0.25 vCPU / 0.5 GiB` para la fase 22; escala con `DesiredCount`. |
| Application Load Balancer | USD 17–20 | USD 1.68–1.97 | Incluye horas del ALB y una carga baja de LCU. |
| ECR | USD 1–2 | USD 0.10–0.20 | Se reutilizan los repositorios backend/worker; depende del tamaño y retención de imágenes. |
| CloudWatch | USD 3–6 | USD 0.30–0.59 | Logs, métricas básicas, NAT y los grupos de IA/notificaciones. |
| S3 + CloudFront | USD 1–3 | USD 0.10–0.30 | Frontend pequeño, pocas solicitudes y baja salida. |
| S3 IA/archive | USD 0.50–3 | USD 0.05–0.30 | Bucket privado con versionado y ciclo de vida; depende del volumen retenido y solicitudes. |
| Secrets Manager + SNS opcional | USD 1–4 | USD 0.10–0.39 | Secreto de canales, topic opcional y solicitudes; no incluye destinatarios externos. |
| SES / SMTP / webhooks | USD 0–5+ | USD 0–0.50+ | SES depende del volumen y la región; Slack, Discord, Teams o SMTP pueden tener planes y cargos propios. |
| EBS, snapshots, backups y transferencia | USD 3–5 | USD 0.30–0.49 | Es la partida con mayor variación operacional. |
| Bedrock Converse / Retrieve | Variable; no incluido | Variable | Depende del modelo, tokens de entrada/salida y llamadas de Knowledge Base. |
| OpenSearch / Bedrock Knowledge Base | Opcional; no incluido | Opcional | No se crea en las fases actuales; elegir vector store, embeddings, red y retención antes de presupuestarlo. |
| **Presupuesto objetivo sin Bedrock ni vector store** | **USD 95–120** | **USD 9.37–11.84** | Rango de bajo tráfico para foundation + aplicación + fases 19–22; comprobar el consumo real en Billing. |

El rango por componente no debe interpretarse como una suma automática de todos los máximos: las cifras superiores representan escenarios conservadores y pueden superponerse. El coste de una variante x86 equivalente se estima en **USD 100–130/mes antes de Bedrock**, principalmente por la diferencia de precio de cómputo.

Bedrock es un coste variable por modelo y tokens. Para una previsión offline, use la tarifa vigente del modelo elegido y esta forma de cálculo:

```text
coste Bedrock ≈ (tokens_entrada / 1 000 000 × precio_entrada)
              + (tokens_salida / 1 000 000 × precio_salida)
              + llamadas de Retrieve / Knowledge Base, si aplican
```

El proveedor `rules` no llama a Bedrock y sirve para validar el flujo sin coste de inferencia. El proveedor `bedrock` sólo debe habilitarse después de fijar el `BedrockModelId`, limitar el ARN IAM y establecer presupuestos/alertas de coste.

## Escenario de sólo foundation

Si durante la validación sólo se crea la plantilla actualizada —NAT, RDS, Redis y ECR— sin ECS, ALB ni frontend, el orden de magnitud es **USD 35–55/mes**. Para 72 horas:

```text
72 / 730 = 0.09863 del mes
USD 35–55 × 0.09863 ≈ USD 3.45–5.42 antes de créditos o Free Tier
```

Para la solución completa planificada **sin inferencia Bedrock ni vector store**:

```text
USD 95–120 × (72 / 730) ≈ USD 9.37–11.84 antes de créditos o Free Tier
```

El importe real de Bedrock debe añadirse según tokens y modelo; no debe extrapolarse linealmente desde las 72 horas si la carga de análisis cambia.

La creación de una pila de CloudFormation no añade por sí misma un cargo de servicio; se facturan los recursos que la pila crea. Almacenamiento, snapshots, logs, IP pública, transferencia y otros consumos pueden continuar aunque el cómputo se use sólo unas horas.

## Cuenta nueva, Free Tier y créditos

Una cuenta nueva puede tener Free Tier o créditos promocionales, pero la elegibilidad depende de la fecha de alta, el plan de cuenta, la región y las condiciones vigentes. Por eso se deben conservar dos cifras:

- **Coste bruto de planificación sin Bedrock:** USD 95–120/mes, o USD 9.37–11.84 para 3 días; añadir el consumo de inferencia y recuperación si se habilitan.
- **Coste neto esperado:** puede ser cercano a USD 0–10 para una prueba corta si los créditos cubren los servicios elegibles, pero no se garantiza.

No se debe asumir que todos los componentes son gratuitos. ALB, CloudFront, ECR, CloudWatch, IPv4 pública, transferencia y determinados tamaños de RDS/Redis pueden tener cargos aunque exista Free Tier. Una promoción puede descontar el importe, pero no elimina la necesidad de configurar presupuestos y alarmas de facturación.

Antes de crear la pila:

1. Revisar **Billing → Free Tier** y **Billing → Credits** de la cuenta concreta.
2. Crear un presupuesto mensual bajo con alerta de uso y coste.
3. Confirmar que la región seleccionada sea `us-east-1`.
4. Usar secretos generados fuera del repositorio; nunca poner credenciales reales en `parameters.example.json` o `.env` versionado.
5. Recordar que la plantilla mantiene RDS, Redis y ECR con `DeletionPolicy: Retain`; borrar la pila no necesariamente detiene ni elimina esos recursos.

## Costes y riesgos de la decisión NAT

La NAT instance `t4g.micro` es apropiada para staging temporal porque reduce el coste frente a un NAT Gateway y permite usar ARM64. A cambio:

- Es un único punto de fallo; no hay failover automático.
- La capacidad de red y CPU es limitada.
- Requiere `SourceDestCheck: false`, forwarding IPv4, iptables persistente y rutas privadas hacia la instancia.
- La IPv4 pública se factura según las reglas vigentes aunque el tráfico sea bajo.
- Producción debe evaluar NAT Gateway o un diseño redundante por AZ.

`t4g.nano` puede bajar ligeramente el coste de cómputo, pero sus 0.5 GiB de memoria y menor baseline de CPU dejan poco margen para el bootstrap, CloudWatch Agent y operaciones. Por eso el parámetro predeterminado es `t4g.micro`.

## Limpieza después de la prueba de 3 días

La prueba no debe terminar sólo con `DeleteStack`:

- Vaciar y eliminar buckets S3 de prueba.
- Eliminar servicios, tareas, ALB, target groups, CloudFront y registros DNS de las capas posteriores.
- Confirmar que no haya tareas ECS activas ni snapshots innecesarios.
- Para RDS y Redis, decidir si se conserva un snapshot o si se eliminan explícitamente. La política `Retain` puede dejar recursos facturables fuera de la pila.
- Eliminar manualmente los repositorios ECR retenidos y sus imágenes si ya no son necesarios.
- Liberar la Elastic IP si quedó asignada o fuera de uso.
- Confirmar en Cost Explorer/Billing que no existan recursos activos, volúmenes, backups, logs o IP públicas.

## Rollback y control operativo

1. Crear Change Set y revisar reemplazos antes de aplicar cambios.
2. Desplegar primero la foundation y comprobar outputs de VPC, rutas, NAT, RDS, Redis y ECR.
3. Validar conectividad desde una tarea backend antes de migrar datos.
4. Si falla el bootstrap de la NAT, revisar SSM/CloudWatch y no continuar con ECS hasta corregir las rutas.
5. Antes de eliminar datos, tomar snapshot y registrar los identificadores fuera del repositorio.
6. Si el stack se elimina, auditar los recursos `Retain` y limpiar los que ya no sean necesarios.

## Fuentes oficiales para verificar precios y elegibilidad

- [AWS Pricing Calculator API](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bcm-pricing-calculator.html)
- [AWS Calculator — supuestos](https://aws.amazon.com/es/calculator/calculator-assumptions/)
- [AWS Free Tier](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier.html)
- [EC2 T4g](https://aws.amazon.com/ec2/instance-types/t4/)
- [NAT instances](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_NAT_Instance.html)
- [VPC e IPv4 pública](https://aws.amazon.com/vpc/pricing/)
- [AWS Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
- [Amazon S3 pricing](https://aws.amazon.com/s3/pricing/)
- [Amazon SNS pricing](https://aws.amazon.com/sns/pricing/)
- [Amazon SES pricing](https://aws.amazon.com/ses/pricing/)
- [AWS Fargate](https://aws.amazon.com/fargate/pricing/)
- [Application Load Balancer](https://aws.amazon.com/elasticloadbalancing/pricing/)

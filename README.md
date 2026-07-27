<div align="center">

<p>
  <img src="Imagenes/1769717477540.png" alt="SentinelMonitorIA · AWS Kiro · Agentic AI Systems" width="900">
</p>

<p>
  <img src="docs/jury/logos/logo%20aws.png" alt="Amazon Web Services" height="54">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="docs/jury/logos/logo2%20codigo%20facilito.png" alt="Código Facilito" height="54">
</p>

# SentinelMonitorIA

### Observabilidad inteligente y AIOps para convertir telemetría en decisiones operativas

**Plataforma multi-tenant desplegada y operativa en Amazon Web Services**, capaz de recibir métricas, logs y eventos, procesarlos de forma asíncrona, detectar incidentes, generar alertas explicables y responder consultas operativas mediante Amazon Lex V2.

<p>
  <img alt="AWS desplegado" src="https://img.shields.io/badge/AWS-DESPLEGADO-FF9900?style=for-the-badge&logo=amazonwebservices&logoColor=white">
  <img alt="Staging operativo" src="https://img.shields.io/badge/STAGING-OPERATIVO-16803c?style=for-the-badge">
  <img alt="Región AWS" src="https://img.shields.io/badge/REGIÓN-us--east--1-232F3E?style=for-the-badge">
  <img alt="Cuenta AWS nueva" src="https://img.shields.io/badge/CUENTA_AWS-NUEVA-7c3aed?style=for-the-badge">
</p>

<p>
  <img alt="Backend" src="https://img.shields.io/badge/BACKEND-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="Frontend" src="https://img.shields.io/badge/FRONTEND-React_+_Vite-61DAFB?style=flat-square&logo=react&logoColor=111827">
  <img alt="Cómputo" src="https://img.shields.io/badge/COMPUTE-ECS_Fargate_ARM64-FF9900?style=flat-square&logo=amazonaws&logoColor=white">
  <img alt="Conversación" src="https://img.shields.io/badge/CHAT-Amazon_Lex_V2-4f46e5?style=flat-square">
  <img alt="Infraestructura" src="https://img.shields.io/badge/IaC-23_fases_CloudFormation-8b5cf6?style=flat-square">
  <img alt="Licencia" src="https://img.shields.io/badge/LICENCIA-Apache_2.0-111827?style=flat-square">
</p>

<p>
  <a href="http://sentinelmonitoria-staging-demo-952763303883-20260726060638.s3-website-us-east-1.amazonaws.com"><strong>Abrir demostración en AWS</strong></a>
  &nbsp;·&nbsp;
  <a href="http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/health"><strong>Verificar health</strong></a>
  &nbsp;·&nbsp;
  <a href="docs/jury/SentinelMonitorIA-Dossier-Jurado-AWS-Codigo-Facilito.pdf"><strong>Leer dossier del jurado</strong></a>
  &nbsp;·&nbsp;
  <a href="docs/architecture/sentinelmonitoria-aws-infrastructure.md"><strong>Explorar arquitectura</strong></a>
</p>

</div>

> [!IMPORTANT]
> **SentinelMonitorIA ya está desplegado y validado en Amazon Web Services.** El entorno funciona en la cuenta AWS nueva `952763303883`, activada ayer, **25 de julio de 2026**, en la región `us-east-1`. En esta cuenta ya operan el frontend S3, el ALB, ECS/Fargate, RDS PostgreSQL, ElastiCache Redis TLS, Amazon Lex V2 y el pipeline asíncrono de análisis y alertas.

> [!NOTE]
> **Última actualización ejecutiva:** 26 de julio de 2026, 21:46 (UTC-05:00). Este README diferencia con precisión las capacidades desplegadas, las extensiones preparadas y los componentes pendientes de autorización. El staging es temporal y demostrativo; no se presenta como producción.

## Resumen ejecutivo

<table>
  <tr>
    <td width="25%" align="center"><strong>DESPLIEGUE REAL</strong><br><code>AWS us-east-1</code><br>Cuenta nueva activada el 25/07/2026</td>
    <td width="25%" align="center"><strong>PIPELINE ASÍNCRONO</strong><br><code>HTTP 202</code><br>Redis Streams + workers ECS</td>
    <td width="25%" align="center"><strong>AIOPS EXPLICABLE</strong><br><code>AIAnalysis → Alert</code><br>Reglas, evidencia y deduplicación</td>
    <td width="25%" align="center"><strong>CHAT OPERATIVO</strong><br><code>Amazon Lex V2</code><br>Español <code>es_419</code> y aislamiento por organización</td>
  </tr>
</table>

SentinelMonitorIA convierte telemetría dispersa en una secuencia operativa trazable: **recibe señales, desacopla el procesamiento, persiste evidencia, detecta anomalías, genera alertas y permite consultarlas conversacionalmente**. El proyecto combina una experiencia ejecutiva para operadores con una base técnica auditable mediante CloudFormation, IAM, Secrets Manager, redes privadas y servicios administrados de AWS.

> **Resultado para el jurado:** no se presenta únicamente un diseño o un prototipo local. Se presenta un MVP desplegado en AWS, navegable desde Internet, con servicios backend activos, datos persistidos, una fuente sintética controlada en EC2 y evidencia comprobada del recorrido `telemetry → AIAnalysis → Alert`.

### Evidencia operativa verificable

| Dimensión | Evidencia actual |
|---|---|
| Despliegue AWS | Cuenta `952763303883`, región `us-east-1`, frontend S3 Website y ALB públicos. |
| Cómputo | Backend, telemetry worker y AI worker activos en ECS/Fargate; imágenes ARM64 publicadas en ECR. |
| Datos | RDS PostgreSQL privado y ElastiCache Redis privado con TLS. |
| Ingesta | `POST /api/v1/telemetry` validado con respuesta `202 Accepted`. |
| Inteligencia | Reglas determinísticas crean `AIAnalysis` y `Alert` con `analysis_id`, hallazgos y recomendaciones. |
| Conversación | Amazon Lex V2 validado con `OpenAlertsIntent`, confianza `0.9` y locale `es_419`. |
| Seguridad | JWT, API keys con scopes, Secrets Manager, IAM Task Roles, subnets privadas y administración EC2 mediante SSM sin SSH. |
| Infraestructura como código | 23 fases CloudFormation numeradas `00`–`22`, con separación explícita entre base, HTTPS, IA/RAG y notificaciones. |
| Control de efectos externos | `AI_ENABLE_ACTIONS=false`; notification worker `0/0`; no se envían correos, chats ni webhooks durante la evaluación. |

### Valor diferencial

- **Prueba de extremo a extremo:** la alerta visible nace de un batch real aceptado por la API, no de datos pintados únicamente en el frontend.
- **IA con límites claros:** las reglas funcionan hoy; Bedrock y RAG se documentan como evolución pendiente de autorización, sin exagerar capacidades.
- **Multi-tenancy desde el diseño:** usuarios, API keys, conversaciones, análisis y alertas se filtran por organización.
- **Seguridad demostrable:** no hay SSH para el productor, las tareas ECS son privadas y los secretos no viven en las imágenes.
- **Evolución sin reconstrucción:** el mismo diseño modular permite pasar de staging HTTP a CloudFront, HTTPS, WAF, alta disponibilidad y Bedrock cuando la cuenta lo autorice.
- **Gobierno de costes:** ARM64, una NAT instance controlada y workers opcionales reducen el gasto del entorno temporal.

## Recorrido ejecutivo para el jurado

| Paso | Qué abrir | Qué demuestra |
|---:|---|---|
| 1 | [Frontend desplegado en AWS](http://sentinelmonitoria-staging-demo-952763303883-20260726060638.s3-website-us-east-1.amazonaws.com) | Aplicación pública, autenticación, dashboard y experiencia de usuario. |
| 2 | [Health del backend](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/health) | Conectividad efectiva con PostgreSQL, Redis y telemetry. |
| 3 | Chat **Ask Sentinel** | Comprensión de intenciones mediante Lex V2 y respuestas limitadas por organización. |
| 4 | Vista de alertas | Evidencia `AIAnalysis → Alert`, severidad, regla y `analysis_id`. |
| 5 | [Diagrama completo de AWS](Diagrama%20de%20arquitectura/Infraestructura%20Completo.png) | Red, cómputo, datos, seguridad, entrada pública y evolución objetivo. |
| 6 | [Dossier técnico](docs/jury/SentinelMonitorIA-Dossier-Jurado-AWS-Codigo-Facilito.pdf) · [Guion de video](docs/jury/SentinelMonitorIA-Guion-Video-Jurado.pdf) | Evidencia consolidada y relato reproducible de cinco minutos. |

<p align="center">
  <a href="#arquitectura-aws-visual">Arquitectura</a> ·
  <a href="#objetivo-general-y-capacidades-de-la-arquitectura-aws">Capacidades AWS</a> ·
  <a href="#guía-de-demostración-para-el-jurado">Demo del jurado</a> ·
  <a href="#cómo-funciona">Flujo técnico</a> ·
  <a href="#estado-del-proyecto">Estado</a> ·
  <a href="#inicio-rápido-en-windows">Ejecución local</a> ·
  <a href="#roadmap">Roadmap</a>
</p>

## Navegación documental

Toda la evidencia está organizada para que el jurado pueda pasar de la visión ejecutiva al detalle técnico sin perder trazabilidad.

| Ruta de lectura | Documento principal | Complementos |
|---|---|---|
| Evaluación ejecutiva | [Dossier técnico AWS y Código Facilito](docs/jury/SentinelMonitorIA-Dossier-Jurado-AWS-Codigo-Facilito.pdf) | [Guion del video de cinco minutos](docs/jury/SentinelMonitorIA-Guion-Video-Jurado.pdf) · [dossier editable](docs/jury/SentinelMonitorIA-Dossier-Jurado-AWS-Codigo-Facilito.md) · [guion editable](docs/jury/SentinelMonitorIA-Guion-Video-Jurado.md) |
| Arquitectura | [Diagrama completo de infraestructura AWS](docs/architecture/sentinelmonitoria-aws-infrastructure.md) | [Draw.io editable](docs/architecture/sentinelmonitoria-aws-architecture.drawio) · [vista Markdown](docs/architecture/sentinelmonitoria-aws-architecture.md) |
| Operación AWS | [MVP staging: acceso, URLs y evidencia](docs/deployment/mvp-staging.md) | [Estimación de costes](docs/deployment/aws-monthly-estimate.md) |
| Infraestructura como código | [Plan CloudFormation por fases](docs/deployment/cloudformation-phased-plan.md) | [Índice de despliegue](docs/deployment/README.md) · [stacks modulares](infra/cloudformation/phases/README.md) · [foundation](infra/cloudformation/README.md) |
| Calidad y operación local | [Runbook local/preproducción](docs/operations/local-runbook.md) | [Informe de validación](docs/operations/local-validation-report.md) · [registro consolidado](docs/operations/project-delivery-record.md) |
| Índice general | [Documentación centralizada](docs/README.md) | [Índice de arquitectura](docs/architecture/README.md) |


## Arquitectura AWS visual

<p align="center">
  <a href="docs/architecture/sentinelmonitoria-aws-architecture.drawio">
    <img src="Diagrama%20de%20arquitectura/Infraestructura%20Completo.png" alt="Diagrama completo de infraestructura AWS de SentinelMonitorIA con iconos oficiales" width="1200">
  </a>
</p>

<p align="center">
  <strong>Vista visual de la plataforma AWS, el frontend de SentinelMonitorIA y sus servicios de red, cómputo, datos y seguridad.</strong><br>
  <a href="docs/architecture/sentinelmonitoria-aws-architecture.drawio">Abrir fuente editable Draw.io</a> ·
  <a href="docs/architecture/sentinelmonitoria-aws-infrastructure.md">Leer diagrama completo en Markdown</a> ·
  <a href="docs/deployment/mvp-staging.md">Consultar estado operativo del staging</a>
</p>

> **Cómo interpretar la imagen:** la composición representa la arquitectura AWS preparada con borde HTTPS/CloudFront, S3 privado, ALB, VPC, ECS, RDS, Redis, IAM, secretos y logs. El staging funcional actual utiliza temporalmente **S3 Website HTTP directo + ALB HTTP/80**; CloudFront, dominio/HTTPS y Bedrock autorizado siguen pendientes. La vista de estado real está documentada en el [diagrama completo de infraestructura](docs/architecture/sentinelmonitoria-aws-infrastructure.md).


La infraestructura ya está **desplegada y operativa en Amazon Web Services** dentro de la cuenta nueva `952763303883`, activada el **25 de julio de 2026**, en `us-east-1`. El recorrido validado usa S3 Website HTTP para el frontend y un ALB HTTP/80 hacia tareas privadas de ECS; RDS PostgreSQL, Redis TLS, Lex V2 y el AI worker con fallback determinístico participan en el flujo comprobado. Amplify fue retirado. CloudFront, dominio/HTTPS y Bedrock generativo permanecen pendientes de verificación o autorización de la cuenta nueva. La foundation monolítica y los stacks modulares siguen siendo alternativas excluyentes para un mismo entorno.

## Objetivo general y capacidades de la arquitectura AWS

El objetivo de SentinelMonitorIA es desplegar una plataforma de observabilidad y AIOps **segura, desacoplada, escalable y gobernable**, capaz de ingerir métricas, logs y eventos, procesarlos de forma asíncrona, detectar incidentes, crear explicaciones operativas y asistir a los operadores mediante conversación en lenguaje natural.

> **Clasificación de estado:** la arquitectura objetivo está representada en el diagrama `Infraestructura Completo`. El staging validado demuestra el núcleo funcional con S3 Website HTTP, ALB HTTP/80, ECS, RDS, Redis TLS, Lex V2 y reglas determinísticas. Alta disponibilidad Multi-AZ, autoscaling, HTTPS/CloudFront, WAF, Bedrock autorizado y RAG siguen siendo fases de evolución.

### ¿Qué se consigue con esta arquitectura?

#### A. Ingesta no bloqueante y procesamiento asíncrono

**Confirmado en staging:**

- `POST /api/v1/telemetry` autentica el agente y responde `HTTP 202 Accepted` sin esperar el análisis completo.
- La telemetría se publica en Redis Streams y los workers consumen el flujo por separado.
- El telemetry worker persiste el batch, métricas, logs y eventos en RDS PostgreSQL y publica la referencia `ai_analysis` después de confirmar la persistencia.
- El AI worker procesa el backlog independientemente de la solicitud HTTP.

El desacoplamiento permite absorber picos dentro de la capacidad de Redis y de los consumers. La absorción de picos masivos no es ilimitada en el staging actual: Redis es un nodo de staging, ECS mantiene una tarea por worker y todavía no existe autoscaling avanzado.

#### B. Detección AIOps y reglas determinísticas

**Confirmado:**

- CPU con unidad `percent` mayor o igual a `90`.
- Memoria con unidad `percent` mayor o igual a `90`.
- Logs con nivel `error` o `fatal`.
- Eventos con severidad `high` o `critical`.
- Correlación y deduplicación mediante organización y `batch_id`.
- Persistencia de `AIAnalysis`, `Alert`, hallazgos, recomendaciones y `analysis_id`.

La detección determinística es el camino operativo actual. **Lex V2 no es el motor de detección:** interpreta intenciones del chat. **Bedrock sería el proveedor generativo de explicaciones y RAG**, pero permanece bloqueado por autorización de cuenta/modelo.

#### C. Aislamiento de red y seguridad

**Confirmado en el diseño y staging:**

- ECS, RDS PostgreSQL y ElastiCache Redis están en subnets privadas sin IP pública en las tareas ECS.
- El API público entra por el ALB y llega al backend en TCP `8000`.
- RDS sólo recibe tráfico privado en `5432`.
- Redis usa TLS en `6379` y la aplicación utiliza `REDIS_TLS=true`/`rediss://`.
- Secrets Manager e IAM Task Roles gestionan secretos y permisos en runtime.
- La EC2 del productor se administra mediante SSM, sin abrir SSH/puerto `22`.
- La sesión de aplicación usa JWT; la API key del productor está limitada al scope `telemetry:write`.
- El backend filtra consultas por organización para impedir cruces de datos.

En el staging actual, el frontend estático se sirve desde S3 Website HTTP y la API desde ALB HTTP/80. La afirmación “todo tráfico público pasa por el ALB” aplica a la API; los archivos estáticos se entregan directamente desde S3 hasta activar CloudFront.

#### D. Eficiencia de costes y ARM64

**Confirmado como decisión de staging:**

- ECS/Fargate e imágenes ECR usan ARM64/Graviton.
- La NAT instance ARM64 reduce el coste frente a un NAT Gateway administrado.
- La configuración es apropiada para un entorno temporal de bajo tráfico.

La NAT instance es un punto único de fallo y no proporciona alta disponibilidad por zona. La arquitectura de producción debe evaluar NAT Gateway o redundancia por AZ, junto con RDS Multi-AZ, Redis con failover y autoscaling.

#### E. Asistencia conversacional multi-tenant

**Confirmado y probado:**

- Lex V2 usa el bot `XFVQNCQTHX`, alias `67MRXD4DQB` y locale `es_419`.
- Están definidas las intenciones `OpenAlertsIntent`, `CriticalAlertsIntent`, `HealthSummaryIntent`, `AssistanceIntent` y `FallbackIntent`.
- La prueba observada devolvió `OpenAlertsIntent`, confianza `0.9` y diálogo `Close`.
- El backend valida el JWT, la organización y el alcance de los datos antes de responder.

Lex V2 realiza comprensión conversacional estructurada; no implica que Bedrock esté habilitado ni que se utilicen embeddings.

#### F. Evolución modular y reproducibilidad

**Confirmado como blueprint de infraestructura:**

- CloudFormation está organizado en 23 fases numeradas `00`–`22`.
- Las fases separan red, NAT, Security Groups, IAM, ECR, datos, secretos, observabilidad, ALB, ECS, frontend, CDN, TLS, RAG y notificaciones.
- La fundación monolítica y los stacks modulares son alternativas excluyentes para un mismo entorno.
- El camino de evolución es staging S3/ALB HTTP → S3 privado/CloudFront/OAC → Route 53/ACM/ALB HTTPS → WAF, Bedrock RAG y servicios de producción.

La existencia de una plantilla no significa que el recurso esté desplegado o autorizado en la cuenta actual.

### Estado resumido: validado frente a objetivo

| Capacidad | Staging actual | Arquitectura objetivo |
|---|---|---|
| Ingesta 202 + Redis Streams | Validado | Escalar consumers y capacidad |
| Reglas y alertas | Validado | Correlación histórica y explicación LLM |
| ECS/RDS/Redis privados | Validado | Multi-AZ, failover y autoscaling |
| Frontend/API | S3 HTTP + ALB HTTP | S3 privado + CloudFront + HTTPS |
| Chat | Lex V2 `es_419` | Lex + proveedor generativo autorizado |
| Bedrock/RAG | No autorizado/no ingerido | Bedrock + Knowledge Base + S3 Vectors |
| Notificaciones | Worker `0/0`, sin destinos externos | Canales aprobados, DLQ y auditoría |
| Acciones automáticas | Desactivadas | Sólo con aprobación, auditoría y rollback |

### Bloqueo de Amazon Bedrock: causa y comprobación

La cuenta devuelve actualmente:

```text
amazon.nova-lite-v1:0        → authorizationStatus=NOT_AUTHORIZED
amazon.titan-embed-text-v2:0 → authorizationStatus=NOT_AUTHORIZED
```

Que la cuenta sea nueva es una **causa probable**, pero no una conclusión suficiente. `NOT_AUTHORIZED` puede representar una combinación de:

1. Verificación o revisión de confianza de una cuenta nueva todavía pendiente.
2. Acceso al modelo no habilitado en `us-east-1`.
3. Permisos IAM insuficientes para el usuario, perfil CLI o ECS Task Role.
4. Permisos de primera activación/suscripción de AWS Marketplace cuando el modelo los requiere.
5. Facturación, método de pago, créditos o activación de servicios todavía pendientes.
6. Restricción de disponibilidad del modelo en la región o de la cuenta.
7. Para RAG, permisos incompletos para `bedrock:Retrieve`, Knowledge Base, S3 o el índice vectorial.

La documentación oficial explica el acceso y los permisos de modelos en [Amazon Bedrock Model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) y los errores de identidad/autorización en [Troubleshooting Amazon Bedrock identity and access](https://docs.aws.amazon.com/bedrock/latest/userguide/security_iam_troubleshoot.html).

Para confirmar la causa exacta se debe revisar en `us-east-1`:

1. **Amazon Bedrock → Model access** y el estado de Nova Lite/Titan Embeddings.
2. Estado de verificación de la cuenta AWS y **Billing/Payment methods**.
3. Permisos del IAM Task Role del AI worker: `bedrock:InvokeModel` y, para RAG, `bedrock:Retrieve`/acceso a Knowledge Base y S3.
4. CloudTrail para identificar el principal y el motivo exacto del `AccessDenied`.
5. Disponibilidad del modelo mediante `get-foundation-model-availability`.

Hasta que el estado sea `AUTHORIZED`, el AI worker permanece correctamente en fallback determinístico: crea análisis y alertas sin inventar una integración Bedrock activa. Lex V2 sigue funcionando de manera independiente.

## Qué es SentinelMonitorIA

SentinelMonitorIA es una plataforma multi-tenant de observabilidad y AIOps con un **MVP desplegado en AWS** y un entorno local reproducible para desarrollo y validación. Su recorrido operativo principal en la nube es:

```text
Usuario/agente → S3 frontend o API key → ALB → ECS/Fargate → Redis Streams
                                                        ├→ RDS PostgreSQL
                                                        └→ AIAnalysis → Alert → dashboard/Lex V2
```

La plataforma permite autenticar operadores, administrar organizaciones, emitir API keys con scopes, conectar agentes, recibir métricas/logs/eventos y convertir señales en alertas explicables. En AWS, el backend y los workers privados procesan el flujo; localmente, Docker Compose reproduce los mismos contratos para desarrollo seguro.

### Qué puedes hacer hoy

| Capacidad | Resultado actual |
|---|---|
| Gestionar acceso | Registro, login, refresh, `/me`, logout y cambio de contraseña. |
| Organizar datos | Crear una organización inicial y asociar usuarios a ella. |
| Conectar agentes | Emitir, listar, rotar y revocar API keys desde `Connections`; las keys tienen scopes explícitos. |
| Recibir observabilidad | Ingerir métricas, logs y eventos mediante `/api/v1/telemetry`. |
| Operar el entorno | Consultar health, métricas, colas mock y servicios Docker. |
| Analizar y notificar | Ejecutar reglas locales, generar alertas, reconocerlas y probar entregas multicanal sin acciones automáticas. |
| Consultar el sistema | Usar el chatbot autenticado con contexto limitado por organización; en local usa `rules` y en staging usa Lex V2 (`es_419`) con fallback determinístico. |
| Evaluar en AWS | Abrir el frontend S3, validar el ALB, consultar health/Swagger, conversar con Lex V2 y revisar alertas persistidas. |
| Trabajar localmente | Reproducir backend, frontend, PostgreSQL, Redis y workers con Windows + Docker Compose. |

### Qué representa ahora

El proyecto ya no es únicamente una preparación local: combina un **staging funcional desplegado en AWS** con un entorno Docker reproducible. La plataforma AIOps asíncrona incluye reglas para CPU, memoria, logs y eventos; persistencia de `AIAnalysis`, `Alert` y `NotificationDelivery`; deduplicación, reintentos, dead-letter, chatbot autenticado y contratos multicanal. Las acciones automáticas permanecen desactivadas (`AI_ENABLE_ACTIONS=false` y `CHAT_ENABLE_ACTIONS=false`) para que la demostración sea segura.

La ruta AWS está definida en 23 stacks CloudFormation numerados `00`–`22`. En la cuenta nueva se desplegaron y validaron la red, seguridad, IAM, ECR, RDS, Redis TLS, secretos, observabilidad, ALB, ECS backend/workers, Lex V2 y frontend S3. Amplify fue eliminado del recorrido; el frontend se publica directamente en S3 Website. CloudFront y Bedrock siguen bloqueados por verificaciones/autorizaciones de la cuenta, no por ausencia de implementación en el repositorio.

- `00`–`13`: red, NAT, seguridad, IAM, ECR, RDS, Redis TLS, secretos, observabilidad, ALB, ECS, backend, workers y S3; base usada por staging.
- `14`: CloudFront; preparado, pero bloqueado por verificación de cuenta.
- `15`–`18`: Route 53, ACM, HTTPS y registros DNS para un dominio propio; opcionales y no activos.
- `19`–`22`: plataforma IA, integración Lex V2, corpus/Knowledge Base y workers; el AI worker está activo con fallback local, el notification worker está apagado y Bedrock sigue pendiente de autorización.

La fase 14 permitiría comenzar con el DNS predeterminado `*.cloudfront.net`, sin dominio propio, si AWS habilita CloudFront. La validación read-only de Bedrock devolvió `NOT_AUTHORIZED` para todos los candidatos consultados: Nova Micro, Nova Lite, Nova 2 Lite, Titan Embeddings V1/V2, Ministral 3B, Mistral 7B y Llama 3.1 8B. No se aceptaron acuerdos, no se invocó ningún modelo alternativo y no se modificó la Knowledge Base. El AI worker permanece en `DesiredCount=1`/`Running=1` usando fallback determinístico; `AI_ENABLE_ACTIONS=false` y el notification worker permanece en `DesiredCount=0`/`Running=0`. El detalle operativo y las URLs actuales están en [`docs/deployment/mvp-staging.md`](docs/deployment/mvp-staging.md).

## Guía de demostración para el jurado

Esta sección es el runbook operativo de la demostración **MVP AWS staging**. El entorno es temporal y está orientado exclusivamente a evaluación; no es producción. El recorrido probado utiliza la cuenta de aplicación demo, Lex V2 para el enrutamiento conversacional, reglas determinísticas para el análisis y una fuente sintética controlada en la EC2 existente `test-redes`.

> **Importante sobre estas credenciales:** el jurado solicitó que las credenciales estuvieran disponibles en esta documentación para poder ejecutar la demo. Son credenciales de staging, no de AWS ni de producción. No reutilizarlas fuera de este entorno. Después de la evaluación deben rotarse o revocarse, especialmente si este repositorio se hace público.

### 1. URLs que debe utilizar el jurado

| Recurso | Dirección | Uso |
|---|---|---|
| **Frontend recomendado** | [S3 Website](http://sentinelmonitoria-staging-demo-952763303883-20260726060638.s3-website-us-east-1.amazonaws.com) | Login, dashboard, alertas, telemetry y chat. |
| **API base** | `http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com` | ALB HTTP/80 del backend FastAPI. |
| **Swagger** | [API Explorer](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/docs) | Revisar contratos y probar endpoints autenticados. |
| **OpenAPI** | [openapi.json](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/openapi.json) | Contrato JSON de la API. |
| **Health general** | [health](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/health) | PostgreSQL, Redis y motor de telemetry. |
| **Health telemetry** | [telemetry/health](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/telemetry/health) | Estado del procesamiento de telemetry. |
| **Métricas** | [metrics](http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/metrics) | Métricas Prometheus. |

Usar el **S3 Website HTTP** y no el hosting Amplify HTTPS. El ALB de esta demo sólo expone HTTP/80; abrir el frontend HTTPS de Amplify provoca mixed content y el navegador puede bloquear las llamadas al chat o al registro. Si el navegador conserva una versión antigua, hacer `Ctrl+F5` antes de iniciar.

### 2. Credenciales de la demostración

#### Cuenta de aplicación para el dashboard y el chat

Estas credenciales se usan en el formulario de login del frontend, no en AWS:

| Campo | Valor |
|---|---|
| Usuario | `demo.staging.0726065814` |
| Email | `demo.staging.0726065814@example.com` |
| Contraseña | `S3ntinel!Demo2026` |
| Rol | `admin` |
| Organización | Organización demo de staging |
| Organización ID | `871268b3-3238-422b-aeb6-19e06f4bf5a8` |

#### API key del agente sintético

Esta key sólo se utiliza en el productor de telemetry instalado en la EC2. No usarla como Bearer token para `/api/v1/chat`, `/api/v1/auth/me` o `/api/v1/alerts`; esos endpoints requieren el access JWT obtenido al iniciar sesión.

| Propiedad | Valor |
|---|---|
| Nombre | `Local telemetry agent` |
| Scope | `telemetry:write` |
| Organización ID | `871268b3-3238-422b-aeb6-19e06f4bf5a8` |
| Endpoint | `http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com/api/v1/telemetry` |
| Token | Ver el bloque de copia siguiente |

```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhOGM4MzM0Zi01MGZmLTQ5N2QtODVkZC03YTAwYjA2NWI2ZDAiLCJ1c2VybmFtZSI6ImRlbW8uc3RhZ2luZy4wNzI2MDY1ODE0IiwidHlwZSI6ImFwaV9rZXkiLCJuYW1lIjoiTG9jYWwgdGVsZW1ldHJ5IGFnZW50Iiwib3JnIjoiODcxMjY4YjMtMzIzOC00MjJiLWFlYjYtMTllMDZmNGJmNWE4Iiwic2NvcGVzIjpbInRlbGVtZXRyeTp3cml0ZSJdLCJleHAiOjE4MTY2NDEyMjEsImlhdCI6MTc4NTEwNTIyMSwianRpIjoiNmNkMzk2NzUtMTllNy00ZWM0LWE5YzItMjJmOWJkM2VlNWE4In0.qoZHpYKu2l3HNfuXCQGTcx2qIlrQ32a07ELBIZ13zZ4
```

La key está asociada a la misma organización del usuario demo. El backend comprueba firma JWT, tipo `api_key`, digest persistido, usuario activo, organización activa, expiración y `telemetry:write` antes de aceptar un batch. El valor de la key no está incluido en los scripts fuente; en la EC2 se encuentra únicamente en `/etc/sentinel-mvp/producer.env` con permisos `0600`.

### 3. Recorrido recomendado de cinco minutos

1. Abrir el [S3 Website](http://sentinelmonitoria-staging-demo-952763303883-20260726060638.s3-website-us-east-1.amazonaws.com).
2. Hacer `Ctrl+F5`.
3. Iniciar sesión con `demo.staging.0726065814` y la contraseña documentada arriba.
4. Revisar el dashboard: PostgreSQL, Redis, telemetry y colas deben aparecer saludables.
5. Abrir el chat **Ask Sentinel** y comprobar el footer:

   ```text
   Lex V2 · es_419 · flujo estructurado · lectura segura
   ```

6. Probar preguntas en español:
   - `¿Cuántas alertas abiertas hay?`
   - `Resume las alertas críticas.`
   - `Revisa el estado de telemetry.`
   - `¿Qué puedes hacer?`
7. Ir a la vista de alertas y actualizarla. El agente sintético debe aparecer con el identificador `ec2-test-redes-synthetic`; las alertas generadas por el incidente tienen severidad `high`.
8. Abrir una alerta para mostrar su evidencia y, si se desea, usar **Acknowledge**. Reconocer una alerta sólo cambia su estado; no ejecuta acciones operativas.
9. Volver al dashboard y mostrar que la cola de notificaciones permanece vacía: no se envían correos, Slack, Discord, Teams ni webhooks.

El usuario demo obtiene un access JWT al iniciar sesión. Si `/api/v1/chat` muestra `401`, cerrar sesión, limpiar la sesión del navegador y autenticarse de nuevo; la API key del agente no sirve para este endpoint.

### 4. Lex V2 sin Bedrock ni embeddings

Lex V2 realiza exclusivamente la comprensión conversacional estructurada:

| Propiedad | Valor validado |
|---|---|
| Bot | `XFVQNCQTHX` |
| Alias | `67MRXD4DQB` (`staging`) |
| Locale | `es_419` |
| Intent probado | `OpenAlertsIntent` |
| Confianza observada | `0.9` |
| Estado de diálogo | `Close` |

El bot contiene las intenciones `OpenAlertsIntent`, `CriticalAlertsIntent`, `HealthSummaryIntent`, `AssistanceIntent` y `FallbackIntent`. Lex identifica la intención, solicita/valida slots cuando el flujo los requiere y entrega al backend una solicitud estructurada. El backend conserva la autorización JWT, el aislamiento por organización, el contexto limitado y la auditoría.

En esta fase **no se invoca Bedrock, no se usan embeddings y no se modifica la Knowledge Base**. La respuesta operativa se produce mediante reglas locales. `lex_bedrock` es el identificador interno heredado del proveedor del backend; la interfaz lo traduce deliberadamente a la etiqueta visible `Lex V2 · es_419 · flujo estructurado · lectura segura` para no confundir al jurado con Bedrock.

Para validar Lex directamente desde AWS CLI, con el perfil autorizado:

```powershell
aws lexv2-runtime recognize-text `
  --bot-id XFVQNCQTHX `
  --bot-alias-id 67MRXD4DQB `
  --locale-id es_419 `
  --session-id ("jury-" + [guid]::NewGuid().ToString()) `
  --text "Cuantas alertas abiertas hay" `
  --region us-east-1 `
  --profile sentinel-monitoria
```

### 5. Productor sintético controlado

La fuente sintética corre en la instancia existente:

| Propiedad | Valor |
|---|---|
| Nombre EC2 | `test-redes` |
| Instance ID | `i-0c56b84145cd08d22` |
| Tipo | `t3.micro` |
| Sistema | Amazon Linux 2023, `x86_64` |
| Administración | AWS Systems Manager, sin SSH ni puertos nuevos |
| Usuario del servicio | `sentinel-demo` |
| Directorio | `/opt/sentinel-mvp` |
| Script remoto | `/opt/sentinel-mvp/mvp-demo-producer.py` |
| Unidad systemd | `sentinel-mvp-demo-producer.service` |
| Archivo de entorno | `/etc/sentinel-mvp/producer.env` |
| Agent ID | `ec2-test-redes-synthetic` |
| Hostname telemetry | `test-redes` |
| Versión | `mvp-demo-producer/1.0` |

El proceso no genera carga real en la máquina: los valores `96%` y `94%` son datos sintéticos enviados al analizador. La instancia se mantiene limitada para que la demo no interfiera con otros servicios:

```ini
Restart=always
RestartSec=30
User=sentinel-demo
CPUQuota=5%
MemoryMax=128M
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
```

#### Frecuencias y contenido

- Al arrancar, envía un heartbeat normal inmediatamente.
- Cada heartbeat posterior ocurre en una ventana aleatoria de **30–60 segundos**.
- Cada incidente ocurre en una ventana aleatoria de **300–600 segundos**, equivalente a **5–10 minutos**.
- El productor reintenta como máximo tres veces con backoff corto; un `401`/`403` detiene los reintentos de ese batch para no inundar la API.
- Después de cada envío prueba `/health` y `/api/v1/telemetry/health`.
- Cada batch usa un `batch_id` UUID distinto.

Telemetry normal:

- CPU sintética aleatoria entre `25%` y `55%`.
- Memoria sintética aleatoria entre `35%` y `65%`.
- Log `info` de heartbeat.
- Evento `synthetic.health.check` con severidad `info`.

Incidente controlado:

- `system.cpu.usage = 96.0`, unidad `percent`.
- `system.memory.usage = 94.0`, unidad `percent`.
- Log con nivel `error`.
- Evento `synthetic.incident` con severidad `high`.
- Detalles marcados como `controlled=true`.

Metadata y tags enviados en todos los batches:

```json
{
  "agent_id": "ec2-test-redes-synthetic",
  "hostname": "test-redes",
  "agent_version": "mvp-demo-producer/1.0",
  "platform": "linux",
  "architecture": "x86_64",
  "tags": {
    "environment": "mvp-demo",
    "synthetic": "true",
    "source": "continuous-demo"
  }
}
```

#### Flujo completo del incidente

```text
EC2 systemd producer
  → POST /api/v1/telemetry (HTTP 202)
  → persistencia TelemetryBatch, Metric, LogEntry y Event
  → Redis Streams / cola ai_analysis
  → ECS AI worker
  → RuleBasedAnomalyDetector
  → AIAnalysis
  → Alert high
  → cola notifications (sin consumer activo)
```

El detector crea findings cuando CPU o memoria con unidad `percent` alcanzan `90%` o más, cuando recibe un log `error`/`fatal` o cuando recibe un evento `high`/`critical`. El incidente sintético activa esas reglas sin usar un modelo generativo.

### 6. Instalación y operación del productor

El instalador local no contiene credenciales. Lee el script, lo comprime y lo copia mediante SSM; crea el usuario no root, el archivo de entorno, la unidad systemd, ejecuta un smoke incident y comprueba el estado:

```powershell
.\scripts\install-mvp-demo-producer.ps1 `
  -ApiKey "API_KEY_DEMO_DOCUMENTADA_EN_ESTA_SECCION" `
  -ApiEndpoint "http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com" `
  -InstanceId "i-0c56b84145cd08d22" `
  -Region "us-east-1" `
  -Profile "sentinel-monitoria"
```

El instalador ejecuta estas acciones en orden:

1. Copia `scripts/mvp-demo-producer.py` a `/opt/sentinel-mvp`.
2. Crea `sentinel-demo` si no existe.
3. Escribe `/etc/sentinel-mvp/producer.env` y fija `root:root`/`0600`.
4. Instala `sentinel-mvp-demo-producer.service` y la habilita para iniciar con el sistema.
5. Ejecuta `sentinel-mvp-demo-smoke.service` como prueba one-shot de incidente.
6. Elimina la unidad temporal del smoke y deja sólo el productor continuo.

Comprobaciones en la EC2, ejecutadas mediante SSM:

```bash
systemctl is-active sentinel-mvp-demo-producer.service
systemctl is-enabled sentinel-mvp-demo-producer.service
systemctl show sentinel-mvp-demo-producer.service \
  -p User -p ActiveState -p SubState -p CPUQuotaPerSecUSec -p MemoryMax
stat -c 'env_mode=%a env_owner=%U:%G' /etc/sentinel-mvp/producer.env
journalctl -u sentinel-mvp-demo-producer.service -n 50 --no-pager -o cat
```

Resultado esperado:

```text
active
enabled
User=sentinel-demo
ActiveState=active
SubState=running
CPUQuotaPerSecUSec=50ms
MemoryMax=134217728
env_mode=600 env_owner=root:root
```

Para detener temporalmente el productor desde una sesión SSM:

```bash
systemctl disable --now sentinel-mvp-demo-producer.service
```

Para reactivarlo sin reinstalarlo:

```bash
systemctl enable --now sentinel-mvp-demo-producer.service
```

No ejecutar `stop`, `disable` ni comandos de limpieza durante la evaluación salvo que se quiera detener deliberadamente la prueba continua.

### 7. Evidencia de validación ya obtenida

| Prueba | Resultado observado |
|---|---|
| Incidente local one-shot con API key | Telemetry HTTP `202`; health HTTP `200`. |
| Smoke incident ejecutado en EC2 | HTTP `202`; health general y telemetry `200`. |
| Productor remoto | Hash instalado igual al hash local; systemd `enabled/active`. |
| `/health` staging | HTTP `200`. |
| `/api/v1/telemetry/health` | HTTP `200`, estado `healthy`. |
| `/metrics` | HTTP `200`. |
| Lex V2 | `OpenAlertsIntent`, confianza `0.9`, diálogo cerrado. |
| Chat autenticado | HTTP `200`, `provider=lex_bedrock`, `conversation_id` presente. |
| Alertas demo | Dos alertas `high` visibles; `rule_id=metric.cpu.high`; `analysis_id` presente. |
| Colas | `telemetry=0`, `alerts=0`, `notifications=0` en la comprobación final. |
| ECS backend | `desired=1`, `running=1`, revisión `5`. |
| ECS telemetry worker | `desired=1`, `running=1`. |
| ECS AI worker | `desired=1`, `running=1`, revisión `3`. |
| ECS notification worker | `desired=0`, `running=0`. |
| Secretos en código fuente | No hay prefijo de API key en los scripts del productor/instalador. |
| `git diff --check` | Correcto. |

La lista de alertas es la evidencia pública del enlace `AIAnalysis → Alert`: cada alerta de inteligencia devuelve `analysis_id`. La cola `ai_analysis` puede mostrar un número distinto de cero porque para esos streams el backend consulta `XLEN`, que representa historial retenido; no debe interpretarse automáticamente como backlog pendiente. La cola `notifications` permanece en cero y no hay consumer de notificaciones activo.

### 8. Notificaciones y límites de seguridad

- `sentinel-monitoria-staging-notification-worker`: `Desired=0`, `Running=0`.
- `notifications` permanece en profundidad `0`.
- `AI_ENABLE_ACTIONS=false`.
- No se envían emails, Slack, Discord, Teams ni webhooks.
- La alerta se persiste y se visualiza, pero ningún componente ejecuta remediación.
- RDS y Redis no cambiaron su infraestructura; la aplicación sí persiste los batches, agentes, análisis y alertas necesarios para la demo.
- No se abrieron puertos en la EC2 ni se modificaron rutas, NAT o security groups.
- La API y el frontend siguen en HTTP temporal; no usar datos reales ni credenciales de producción.
- La API key tiene alcance sólo `telemetry:write`; no concede acceso al chat ni a endpoints administrativos.

### 9. Troubleshooting para el jurado

#### El frontend no carga la información

1. Confirmar que se está usando el enlace S3 HTTP, no Amplify.
2. Ejecutar `Ctrl+F5`.
3. Abrir directamente `/health` y `/api/v1/telemetry/health`.
4. Si ambos devuelven `200`, cerrar sesión y volver a iniciar.

#### `/api/v1/chat` devuelve `401`

La causa es la sesión JWT del navegador, no Lex. Ejecutar en DevTools del sitio S3:

```javascript
localStorage.removeItem("sentinelmonitoria.session");
location.reload();
```

Después autenticarse de nuevo y comprobar que `GET /api/v1/auth/me` devuelve `200`. No usar la API key de telemetry en el chat.

#### No aparece una alerta inmediatamente

El heartbeat normal no genera alertas. Para el incidente, esperar la ventana de `5–10` minutos o ejecutar el smoke one-shot desde SSM. Una vez recibido el `202`, el worker puede tardar unos segundos en persistir `AIAnalysis` y `Alert`; actualizar el dashboard.

#### El dashboard muestra una alerta pero no llega una notificación

Es el comportamiento esperado: el notification worker está apagado y la cola `notifications` se mantiene en `0` por diseño de la demo.

#### La etiqueta dice modo local

Hacer `Ctrl+F5` desde el S3 Website. Si ya se inició sesión antes de publicar el bundle, cerrar sesión y volver a entrar. En staging el footer esperado es `Lex V2 · es_419 · flujo estructurado · lectura segura`; `Modo local · reglas · lectura segura` corresponde al build local.

#### Una key de telemetry devuelve `401`

Confirmar que se copió el token completo, que se envía como `Authorization: Bearer <API_KEY>`, que se usa `/api/v1/telemetry` y que no se intentó usar la key como access JWT. No pegar la key en el chat ni en la consola pública del navegador.

### 10. Coste y cierre de la demostración

Se reutiliza la EC2 `t3.micro` ya encendida, por lo que el coste marginal del productor es prácticamente cero. No se creó un servicio ECS adicional para el productor. El servicio consume una fracción limitada de CPU y memoria; las alertas son datos sintéticos, no carga real.

Después de la evaluación:

1. Detener el servicio systemd mediante SSM.
2. Revocar la API key `Local telemetry agent` desde `Connections` o `/api/v1/auth/api-keys`.
3. Cambiar o desactivar el usuario demo.
4. Eliminar las credenciales de este README si el repositorio se publica fuera del jurado.
5. Revisar y apagar los recursos staging para evitar costes: ECS, RDS, Redis, ALB, S3, CloudWatch y la EC2.

### 11. Archivos que implementan la demo

| Archivo | Responsabilidad |
|---|---|
| `scripts/mvp-demo-producer.py` | Productor estándar, batches normales/incidentes, reintentos, probes de salud y modo `--once`. |
| `scripts/install-mvp-demo-producer.ps1` | Copia por SSM, usuario systemd, env `0600`, límites, smoke test y comprobación de estado. |
| `frontend/src/ChatWidget.jsx` | Etiqueta dinámica `Lex V2`/modo local y proveedor devuelto por el backend. |
| `scripts/publish-frontend.ps1` | Build con `VITE_API_BASE_URL` y `VITE_CHAT_PROVIDER`, publicación S3 Website. |
| `backend/src/api/v1/telemetry.py` | Autenticación de API key e ingesta de batches. |
| `backend/src/services/ai/analyzer.py` | Reglas de CPU, memoria, logs y eventos. |
| `backend/src/services/chat/providers.py` | Enrutamiento Lex V2 y fallback determinístico. |
| `docs/deployment/mvp-staging.md` | Detalle de infraestructura, URLs y estado AWS. |

## Cómo funciona

El flujo completo de una sesión a una ingesta es el siguiente:

```mermaid
flowchart LR
    U[Usuario] --> F[Frontend React/Vite]
    F -->|registro o login| A[FastAPI Auth]
    A --> P[(PostgreSQL)]
    F -->|genera API key| K[API key asociada a organización]
    K --> G[Agente o script externo]
    G -->|Bearer key + batch JSON| T[POST /api/v1/telemetry]
    T --> V[Validación de key, usuario, organización y expiración]
    V --> P
    V --> R[(Redis / rate limiting)]
    V --> Q[Cola asíncrona: Redis Streams AWS / mock o Streams local]
    Q --> W[Workers de telemetry e inteligencia]
    T -->|202 Accepted| G
    F -->|health y estadísticas| H[Health, metrics y telemetry stats]
    H --> P
    H --> R
```

1. **El usuario se registra.** El backend crea el usuario, la organización inicial y la membresía administrativa.
2. **El usuario inicia sesión.** FastAPI entrega un access token y un refresh token; ambos `jti` se registran en PostgreSQL. El frontend restaura la sesión y la renueva mediante rotación de refresh tokens de un solo uso.
3. **Se crea una API key.** La key queda asociada al usuario y a una organización, se muestra completa una sola vez y después solo se expone su metadata.
4. **Un agente envía telemetry.** Utiliza `Authorization: Bearer <API_KEY>` y publica un batch con metadata y métricas, logs o eventos.
5. **El backend valida el acceso.** Comprueba firma JWT, tipo `api_key`, existencia en PostgreSQL, estado activo, expiración, usuario, organización y el scope requerido (`telemetry:write`).
6. **Se registra el agente y el batch.** Si el agente no existe para esa organización, se crea. El batch se persiste y se prepara para procesamiento.
7. **La cola desacopla el trabajo.** AWS utiliza Redis Streams con consumers ECS; el entorno local conserva `QUEUE_PROVIDER=mock` por defecto y permite activar Streams con `docker-compose.redis-worker.yml`.
8. **Los workers procesan y el dashboard observa.** Telemetry persiste los datos, inteligencia crea análisis/alertas y la interfaz consulta health, estadísticas y señales operativas.

La aplicación usa automáticamente `http://localhost:8000/api/v1/telemetry` en el entorno local. No es necesario introducir una URL arbitraria desde `Connections`; una URL personalizada será relevante cuando el backend se publique detrás de otro dominio.

## Estado AWS actual y validación Bedrock

El MVP staging está activo en la cuenta AWS nueva `952763303883`, activada el 25 de julio de 2026, región `us-east-1`, con perfil administrativo `sentinel-monitoria`. Este es el estado real comprobado, posterior a la preparación inicial de CloudFormation:

| Componente | Estado real validado |
|---|---|
| Frontend público | S3 Website HTTP directo en `sentinelmonitoria-staging-demo-952763303883-20260726060638`; Amplify ya no forma parte del flujo y CloudFront no está activo. |
| ALB/ECS | ALB HTTP/80 en `sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com`; backend en revisión de tarea `5`, imagen `v0.1.2`. |
| Lex V2 | Bot `XFVQNCQTHX`, alias `67MRXD4DQB`, locale `es_419`; integrado para el flujo conversacional. |
| AI worker | Revisión `3`, imagen `v0.1.3`, `Desired=1`, `Running=1`; genera con fallback determinístico local mientras Bedrock no está autorizado. |
| Notification worker | `Desired=0`, `Running=0`; las notificaciones permanecen apagadas. |
| RDS y Redis | Se mantienen sin cambios, conforme al alcance aprobado. |
| Bedrock y Knowledge Base | No se aceptaron acuerdos, no se invocó ningún modelo y no se modificó la Knowledge Base. Todos los modelos consultados permanecen `NOT_AUTHORIZED`. |

### Comparación económica de modelos

Los precios siguientes son **On-Demand Standard in-region**, para `us-east-1`, obtenidos del Price List oficial de AWS el `23 de julio de 2026` y efectivos desde `1 de julio de 2026`. Se expresan por un millón de tokens; embeddings sólo cobran entrada.

| Modelo / ID | Entrada | Salida | Contexto y modalidad | Evaluación para SentinelMonitorIA |
|---|---:|---:|---|---|
| **Nova Micro** `amazon.nova-micro-v1:0` | **$0.035/M** | $0.14/M | 128K; texto; streaming y Converse | **Candidato principal por coste** para chat breve, clasificación, resumen y análisis textual. Validar calidad de español con prompts reales. |
| Nova Lite `amazon.nova-lite-v1:0` | $0.06/M | $0.24/M | 300K; texto, imagen y vídeo | Alternativa si el análisis necesita entradas multimodales; más cara que Micro. |
| Nova 2 Lite `amazon.nova-2-lite-v1:0` | $0.33/M | $2.75/M | 1M; texto, imagen y vídeo | Gran contexto, pero no es económica para el flujo normal por su coste de salida. |
| **Ministral 3B** `mistral.ministral-3-3b-instruct` | $0.10/M | **$0.10/M** | 256K; texto e imagen; chat, function calling y salidas estructuradas | Alternativa económica para conversación, visión y análisis; medir español frente a Nova Micro antes de elegirla. |
| Mistral 7B `mistral.mistral-7b-instruct-v0:2` | $0.15/M | $0.20/M | Texto; modelo activo en el catálogo | Alternativa válida, pero menos atractiva en coste que Micro/Ministral 3B para este MVP. |
| Llama 3.1 8B `meta.llama3-1-8b-instruct-v1:0` | $0.22/M | $0.22/M | 128K; texto | Referencia de calidad multilingüe: Meta declara soporte de español; no es la opción de menor coste. |
| **Titan Text Embeddings V2** `amazon.titan-embed-text-v2:0` | **$0.02/M** | — | Hasta 8.192 tokens; vectores 1.024, 512 o 256 dimensiones | **Candidato principal para RAG**; optimizado para retrieval. Español está incluido en la vista previa multilingüe, aunque AWS indica que el modelo está optimizado para inglés. |
| Titan Embeddings V1 `amazon.titan-embed-text-v1` | $0.10/M | — | Embeddings de texto | No recomendado frente a V2: cuesta cinco veces más y es la generación anterior. |

Fuentes: [precios de Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/), [ficha de Nova Micro](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-micro.html), [ficha de Nova Lite](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-lite.html), [ficha de Nova 2 Lite](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-lite.html), [embeddings Titan](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html), [ficha de Llama 3.1 8B en Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-meta-llama-3-1-8b-instruct.html), [ficha oficial de Ministral 3B](https://docs.mistral.ai/models/model-cards/ministral-3-3b-25-12) y [model card oficial de Llama 3.1](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md). Content was rephrased for compliance with licensing restrictions.

### Recomendación condicionada, todavía no activada

1. **Generación inicial:** `amazon.nova-micro-v1:0` por su menor coste de entrada y su menor coste total en el patrón esperado de chat/análisis, donde la entrada suele superar a la salida. Si las respuestas fueran excepcionalmente largas, Ministral 3B tiene una salida más barata. Debe pasar una prueba de aceptación en español con respuestas de chat, extracción de señales, análisis de logs y formato `AIAnalysis`.
2. **RAG:** `amazon.titan-embed-text-v2:0`, usando inicialmente 1.024 dimensiones y fragmentos lógicos en español. Debe medirse `recall@k`/relevancia con el corpus real; que el idioma aparezca en la lista de preview no sustituye la validación del dominio.
3. **Alternativa de calidad/conversación:** `mistral.ministral-3-3b-instruct` si la prueba muestra mejor español, chat o visión a cambio de un coste todavía bajo. `meta.llama3-1-8b-instruct-v1:0` queda como referencia si se prioriza calidad multilingüe sobre coste.
4. **Bloqueo operativo:** todos los candidatos continúan `NOT_AUTHORIZED`. No cambiar `AI_MODEL_ID`, no aceptar acuerdos, no desplegar otro modelo, no iniciar ingesta de Knowledge Base y no invocar Bedrock hasta recibir confirmación explícita y completar la prueba en español.

## Inteligencia y alertas

La ingesta no espera a un modelo. Cuando se activa Redis Streams, el flujo es:

```text
POST /api/v1/telemetry
        │
        ▼
worker telemetry → PostgreSQL
        │
        ▼
cola ai_analysis
        │
        ├── reglas CPU/memoria/logs/eventos
        ├── Ollama local o Bedrock opcional
        └── AIAnalysis + Alert
                    │
                    ▼
             cola notifications
                    │
                    ├── log local
                    ├── Email/SMTP
                    ├── Slack / Discord / Microsoft Teams
                    ├── Webhook firmado
                    └── WebSocket del dashboard
```

Para activar el flujo durable local:

```powershell
docker compose -f backend\docker-compose.yml -f backend\docker-compose.redis-worker.yml up -d --build backend worker ai-worker notification-worker
```

Configuración principal:

| Variable | Local | AWS |
|---|---|---|
| `AI_PROVIDER` | `rules` o `ollama` | `rules` o `bedrock` |
| `AI_MODEL_ID` | No requerido para reglas/Ollama | ID del modelo Bedrock aprobado |
| `AI_KNOWLEDGE_BASE_ID` | Vacío o contexto del batch | Export de la Knowledge Base Bedrock creada por la fase 19 |
| `NOTIFICATION_CHANNELS` | `log`, SMTP o webhooks | `log`, SES/SMTP, Slack, Discord, Teams o webhook |
| `AI_ENABLE_ACTIONS` | `false` | `false` |

Endpoints disponibles:

- `GET /api/v1/alerts`: lista alertas de las organizaciones del usuario.
- `POST /api/v1/alerts/{alert_id}/acknowledge`: reconoce una alerta sin ejecutar acciones.
- `WS /api/v1/alerts/ws`: novedades de alertas para el dashboard; el cliente autentica enviando el JWT en el primer mensaje JSON, no en la URL ni en un query string sensible.

El handshake esperado es:

```json
{
  "type": "authenticate",
  "access_token": "ACCESS_JWT"
}
```

La guía de arquitectura y el contrato de despliegue están en [`docs/architecture/README.md`](docs/architecture/README.md) y [`docs/deployment/cloudformation-phased-plan.md`](docs/deployment/cloudformation-phased-plan.md).

## Chatbot operativo

El dashboard incluye un chat autenticado para consultar el contexto reciente de alertas de la organización. En local usa `CHAT_PROVIDER=rules`, no realiza llamadas externas y mantiene la conversación sólo en memoria del navegador. El endpoint `POST /api/v1/chat` devuelve respuestas normalizadas, sugerencias, fuentes allowlisted y acciones vacías porque las acciones automáticas están deshabilitadas.

La interfaz está separada del proveedor. En AWS, Lex V2 está integrado con locale `es_419` para intenciones y parámetros estructurados; el backend conserva JWT, aislamiento por organización, permisos y auditoría. Bedrock queda reservado para explicaciones generativas y RAG cuando exista autorización y una selección confirmada; el navegador no llama directamente a servicios AWS.

Configuración local:

```env
CHAT_PROVIDER=rules
CHAT_CONTEXT_ALERT_LIMIT=20
CHAT_MAX_MESSAGE_LENGTH=2000
CHAT_ENABLE_ACTIONS=false
```

En el MVP AWS, Lex V2 está activo y el AI worker responde mediante fallback determinístico mientras los modelos Bedrock siguen `NOT_AUTHORIZED`. La Knowledge Base no se ha modificado ni ingerido; las acciones automáticas permanecen deshabilitadas.

## Estado del proyecto

| Área | Estado | Descripción |
|---|---|---|
| Backend FastAPI | Implementado | API local en `http://localhost:8000`. |
| PostgreSQL | Implementado | Persistencia local mediante Docker Compose. |
| Redis | Implementado | Cache, health checks y servicios auxiliares. |
| Cola mock / Redis Streams | Implementado localmente | `mock` sigue siendo el proveedor predeterminado; el override activa streams Redis durables. |
| Worker de telemetry | Implementado localmente | Consumer group, recuperación de pendientes, ACK, reintentos, dead-letter y persistencia PostgreSQL. |
| Motor IA y alertas | Implementado localmente | Reglas de anomalías, `AIAnalysis`, `Alert`, deduplicación y acknowledge autenticado; Ollama/Bedrock opcionales. |
| Notificaciones | Implementado localmente | Worker asíncrono con log, Email/SMTP, Webhook, Slack, Discord, Teams y WebSocket. |
| Frontend React/Vite | Implementado | Dashboard ejecutivo protegido en `http://localhost:3000`. |
| Registro y login | Implementado | Login por username o email, JWT access/refresh y restauración de sesión. |
| API keys | Implementado | Creación, listado, scopes, rotación explícita, revocación y validación persistida para telemetry. |
| Ingestión telemetry | Implementado localmente | Requiere una API key asociada a una organización. |
| Agente Vector | Validado localmente | Configuración normal Vector `0.36.0` validada por esquema; pipeline E2E aislado con fixture JSONL, API key `telemetry:write`, Redis Streams, worker y persistencia PostgreSQL. La ejecución de fuentes host/journald/Docker queda pendiente en un host Linux real. |
| AWS staging base `00`–`13` | **Desplegado y operativo** | Cuenta AWS nueva `952763303883`, activada el 25 de julio de 2026: VPC, NAT instance, IAM, ECR, RDS, Redis TLS, secretos, observabilidad, ALB, ECS backend/workers y S3 Website validados en `us-east-1`. |
| AWS CloudFront `14` | Bloqueado | Preparado, pero la cuenta AWS exige verificación antes de crear recursos CloudFront. |
| AWS dominio `15`–`18` | No activado | Route 53, ACM, HTTPS y DNS propio; requiere dominio, certificados y la habilitación correspondiente. |
| AWS IA/notificaciones `19`–`22` | Parcial / controlado | Lex V2 activo; AI worker en `Desired=1`/`Running=1` con fallback determinístico; Bedrock permanece `NOT_AUTHORIZED`, la Knowledge Base no se modifica y notification worker en `Desired=0`/`Running=0`. |
| Terraform/CDK | Pendiente | Directorios reservados para infraestructura futura. |
| Pruebas automatizadas | Implementado localmente | Backend: 19 pruebas correctas y 1 omitida por requerir Redis Streams; frontend: 9/9; smoke API: 9/9. |
| Validación de infraestructura | Comprobada offline y complementada en staging | 23 templates YAML, matriz JSON, scripts PowerShell, imports/exports y `git diff --check`; los recursos base y endpoints públicos también se verificaron en la cuenta AWS. |

## Alcance AWS y fases de implementación

El diseño AWS usa una estrategia modular y excluyente respecto a `infra/cloudformation/sentinel-monitoria-foundation.yaml`: en un mismo ambiente se despliega la foundation monolítica **o** los stacks por fases, nunca ambos.

| Bloque | Fases | Objetivo | Estado |
|---|---:|---|---|
| Base de aplicación | `00`–`13` | Publicar la aplicación con ECS/Fargate ARM64, RDS, Redis, ALB y S3 Website | Desplegado y validado en staging |
| CloudFront | `14` | Añadir distribución CloudFront con el DNS predeterminado | Bloqueado por la verificación de cuenta AWS |
| Dominio propio | `15`–`18` | Route 53, ACM, HTTPS directo del ALB y registros DNS | No activado; requiere dominio y certificados |
| IA y notificaciones | `19`–`22` | S3 de corpus, integración Lex V2, Knowledge Base/Data Source Bedrock, modelo generativo pendiente, AI worker y notification worker | Parcial; Lex V2 y AI worker con fallback activos, Bedrock `NOT_AUTHORIZED`, Knowledge Base sin cambios y notification worker apagado |

El script `scripts/deploy-cloudformation-phases.ps1` conserva `00–14` como recorrido predeterminado. Las fases `19–22` se ejecutan individualmente con `-Phase` o en conjunto con `-IncludeAiNotifications`; las fases `15–18` no se agregan automáticamente. El validador CloudFormation ofrece la misma selección, pero las llamadas a AWS sólo ocurren cuando se ejecuta explícitamente con credenciales.

No se ejecutará una activación de Bedrock ni de notificaciones sin confirmación explícita. Para una futura habilitación, la secuencia controlada será:

1. Mantener el AI worker con fallback determinístico y el notification worker en `DesiredCount=0`/`Running=0`.
2. Solicitar o completar la autorización del modelo generativo y de Titan V2; comprobar nuevamente `get-foundation-model-availability`.
3. Ejecutar una prueba controlada de español para chat, análisis, formato `AIAnalysis` y retrieval/RAG, sin cambiar RDS ni Redis.
4. Elegir el modelo sólo después de revisar coste, calidad y autorización; actualizar `AI_MODEL_ID` únicamente con aprobación.
5. Ingerir corpus redactado y activar Knowledge Base sólo con aprobación separada; mantener `AI_ENABLE_ACTIONS=false` y notificaciones apagadas.

Redis AWS usa `TransitEncryptionEnabled=true`; por eso ECS envía `REDIS_TLS=true` y el backend/workers usan `rediss://`. La imagen compartida del worker se construye para `linux/arm64`. El objetivo de coste inicial es mantener el staging dentro del presupuesto disponible de USD 100, sin contar variaciones de tráfico o servicios opcionales de Bedrock/vector store.

El MVP AWS staging **ya está desplegado y comprobado mediante llamadas reales a AWS** en la cuenta nueva `952763303883`, activada el 25 de julio de 2026, región `us-east-1`, con el perfil `sentinel-monitoria`. Se verificaron el frontend S3, Lex V2, ALB/ECS, PostgreSQL y Redis mediante la API, Swagger/OpenAPI, registro, autenticación y el fallback seguro del AI worker. CloudFront, Route 53, ACM, HTTPS y Bedrock no están activos debido a las verificaciones y autorizaciones todavía pendientes en la cuenta reciente; Amplify fue eliminado del recorrido. La documentación, los 23 YAML, parámetros JSON y scripts también se comprobaron offline.

## Arquitectura local

```text
┌───────────────────────────────┐
│ React + Vite                  │
│ http://localhost:3000         │
│ Login, dashboard, API keys    │
└───────────────┬───────────────┘
                │ HTTP + CORS + Bearer JWT
                ▼
┌───────────────────────────────┐
│ FastAPI                       │
│ http://localhost:8000         │
│ Auth, health, telemetry       │
└──────────┬────────────┬───────┘
           │            │
           ▼            ▼
┌────────────────┐ ┌────────────────┐
│ PostgreSQL     │ │ Redis          │
│ localhost:5432 │ │ localhost:6379 │
└────────────────┘ └────────────────┘
```

### Flujo de telemetry

```text
Usuario registra organización
        │
        ▼
Genera API key desde Connections
        │
        ▼
Configura endpoint + Bearer key en el agente
        │
        ▼
POST /api/v1/telemetry
        │
        ├── valida JWT API key en PostgreSQL
        ├── comprueba organización y expiración
        ├── crea/actualiza el agente
        └── procesa el batch en la cola mock
```

La API key es un token emitido por SentinelMonitorIA. El usuario no necesita introducir una URL arbitraria para el flujo normal: el sistema muestra automáticamente el endpoint configurado, por ejemplo `http://localhost:8000/api/v1/telemetry`. Una URL personalizada solo será necesaria cuando la instalación esté publicada detrás de otro dominio o cuando se agreguen integraciones externas.

## Estructura del repositorio

```text
SentinelMonitorIA/
├── agent/                         # Agente Vector y flujo E2E local aislado
│   ├── configs/                    # Configuración normal y vector.e2e.toml
│   ├── deploy/                    # Instalador, entrypoint, healthcheck y Compose
│   ├── fixtures/                  # Fixture JSONL métrica/log/evento
│   ├── scripts/                   # Generador PowerShell de batch IDs
│   ├── Dockerfile
│   ├── Dockerfile.e2e
│   └── README.md
├── backend/
│   ├── src/main.py                # Aplicación FastAPI, CORS, health y métricas
│   ├── src/api/v1/                # Routers auth, health y telemetry
│   ├── src/config/                # Settings y logging
│   ├── src/database/              # PostgreSQL async y Redis
│   ├── src/middleware/            # Fachada de compatibilidad para routers antiguos
│   ├── src/models/                # User, Organization, Token y telemetry
│   ├── src/schemas/               # Contratos Pydantic
│   ├── src/services/              # Auth, rate limiter y telemetry
│   ├── tests/                     # Estructura reservada para tests
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── README.md
├── docs/architecture/             # Documentación técnica del agente
├── frontend/
│   ├── src/App.jsx                # Auth, dashboard y Connections
│   ├── src/auth.js                # Sesión, auth y API keys
│   ├── src/api.js                 # Cliente del dashboard y Prometheus parser
│   ├── src/styles.css              # Sistema visual responsive
│   ├── package.json
│   └── vite.config.js
├── infra/                          # Terraform/CDK reservados para futuras fases
├── scripts/                        # Scripts PowerShell de operación local
├── workers/                        # Reservado para consumidores/procesadores
├── .env.example                    # Variables generales y futuras
└── README.md                       # Guía principal
```

## Requisitos

Para el flujo local en Windows:

- Windows 10/11.
- Docker Desktop con el engine iniciado.
- Docker Compose v2 (`docker compose`).
- Node.js y npm para el frontend.
- PowerShell.
- Git opcional.

Versiones usadas durante la validación:

```text
Node.js  v24.14.1
npm      v11.11.0
Vite     v8.1.5
Python   3.12 dentro de la imagen backend
```

El backend se ejecuta dentro de Docker, por lo que no es necesario instalar Python para el flujo recomendado.

## Inicio rápido en Windows

Todos los comandos siguientes deben ejecutarse desde la raíz `SentinelMonitorIA`.

### 1. Verificar Docker

```powershell
.\scripts\check-docker.ps1
```

El script detecta automáticamente la instalación por usuario de Docker Desktop, comprueba el CLI, Compose, el daemon, ejecuta un contenedor `hello-world` y muestra el estado de WSL.

Si Docker no está en el `PATH`, el script intenta añadir automáticamente:

```text
%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin
```

También se puede añadir manualmente a la sesión actual:

```powershell
$env:Path = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;$env:Path"
```

### 2. Iniciar backend y servicios

Primera ejecución o después de cambiar dependencias:

```powershell
.\scripts\start-local.ps1 -Build
```

Ejecuciones posteriores:

```powershell
.\scripts\start-local.ps1
```

Para levantar también el frontend dentro de Docker, sin abrir una segunda terminal:

```powershell
.\scripts\start-local.ps1 -Build -Frontend
```

El modo `-Frontend` usa el override opcional `backend/docker-compose.frontend.yml`, conserva los datos del backend y publica Vite en `http://localhost:3000`. No lo uses mientras exista otro Vite manual ocupando ese puerto.

El script inicia PostgreSQL, Redis, backend, Adminer y Redis Commander. LocalStack no se inicia por defecto.

Comprobar estado:

```powershell
docker compose -f backend\docker-compose.yml ps
Invoke-RestMethod http://localhost:8000/health
```

Para ver logs:

```powershell
docker compose -f backend\docker-compose.yml logs -f backend
```

Para detener servicios sin borrar datos:

```powershell
docker compose -f backend\docker-compose.yml down
```

Para detener y borrar volúmenes locales, incluyendo usuarios y telemetry:

```powershell
.\scripts\start-local.ps1 -Clean
```

`-Clean` es destructivo para el estado local y no debe usarse como rutina.

### 3. Iniciar frontend

La opción manual conserva el flujo Vite actual:

```powershell
Set-Location frontend
npm ci
npm run dev
```

La configuración de Vite usa `localhost:3000` y `strictPort`. Abrir:

```text
http://localhost:3000
```

El frontend usa por defecto:

```text
http://localhost:8000
```

Para usar otra API durante la sesión actual de PowerShell:

```powershell
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

Como alternativa, el frontend puede ejecutarse dentro de Docker junto al stack:

```powershell
# Detener primero cualquier Vite manual que use el puerto 3000
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml up -d --build
Invoke-WebRequest http://localhost:3000/ -UseBasicParsing
```

Para detener el frontend Docker sin borrar datos del backend:

```powershell
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml down
```

Para detener Vite manual, usar `Ctrl+C` en su terminal.

### 4. Ejecutar el E2E real del agente

El flujo Vector → FastAPI → Redis Streams → worker → PostgreSQL está documentado y validado para Windows + Docker en [`agent/README.md`](agent/README.md#flujo-e2e-local-en-windows--docker). Usa un Compose aislado, la red `backend_sentinel-network` y una API key real asociada a una organización con scope `telemetry:write`; no inicia AWS, mock API ni elimina volúmenes.

```powershell
pwsh -File agent/scripts/generate-e2e-fixture.ps1
docker compose -f agent\deploy\docker-compose.e2e.yml up -d --build --force-recreate
docker exec sentinel-redis redis-cli XPENDING sentinel:stream:telemetry sentinel-telemetry-workers
```

El procedimiento completo para crear la key, revisar los tres batches `processed` y repetir la prueba está en la guía del agente.

## Servicios, puertos y datos

| Servicio | URL/puerto | Uso |
|---|---|---|
| Frontend Vite | `http://localhost:3000` | Login, dashboard y conexiones |
| Backend FastAPI | `http://localhost:8000` | API principal |
| Swagger | `http://localhost:8000/api/v1/docs` | Documentación interactiva en desarrollo |
| OpenAPI | `http://localhost:8000/api/v1/openapi.json` | Contrato JSON en desarrollo |
| PostgreSQL | `localhost:5432` | Base de datos |
| Redis | `localhost:6379` | Cache y soporte de servicios |
| Adminer | `http://localhost:8080` | Administración PostgreSQL |
| Redis Commander | `http://localhost:8081` | Administración Redis |
| Metrics | `http://localhost:8000/metrics` | Formato Prometheus |

Credenciales locales de PostgreSQL definidas por Compose:

| Campo | Valor |
|---|---|
| Sistema | PostgreSQL |
| Servidor desde Adminer | `postgres` |
| Servidor desde Windows | `localhost` |
| Usuario | `sentinel` |
| Contraseña | `sentinel123` |
| Base de datos | `sentinelmonitoria` |

Compose crea los volúmenes `postgres_data`, `redis_data` y `backend_logs`. `docker compose down` los conserva; `down -v` o `-Clean` los elimina.

## Configuración

### Configuración efectiva del backend

`backend/docker-compose.yml` proporciona explícitamente las variables necesarias al contenedor. Para ejecutar FastAPI directamente en Windows, copiar el ejemplo:

```powershell
Copy-Item backend\.env.example backend\.env
```

En ejecución directa, el backend necesita PostgreSQL y Redis disponibles en `localhost`. En Compose, los hosts internos son `postgres` y `redis`.

Variables principales:

| Variable | Valor local | Función |
|---|---|---|
| `ENVIRONMENT` | `development` | Activa comportamiento de desarrollo y endpoints dev |
| `DEBUG` | `true` | Publica Swagger, ReDoc y OpenAPI |
| `API_HOST` | `0.0.0.0` | Host de escucha |
| `API_PORT` | `8000` | Puerto del backend |
| `API_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Orígenes permitidos |
| `JWT_SECRET_KEY` | Cambiar en producción | Firma de JWT |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Duración access token |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Duración refresh token |
| `QUEUE_PROVIDER` | `mock` | Proveedor local de cola; el override Redis usa `redis`. |
| `MOCK_QUEUE_MAX_SIZE` | `10000` | Capacidad de colas mock. |
| `REDIS_STREAM_PREFIX` | `sentinel:stream` | Prefijo de streams Redis. |
| `REDIS_STREAM_MAX_LENGTH` | `10000` | Retención máxima aproximada por stream. |
| `REDIS_STREAM_CONSUMER_GROUP` | `sentinel-telemetry-workers` | Consumer group del worker. |
| `TELEMETRY_STALE_BATCH_SECONDS` | `3600` | Antigüedad para reconciliar batches abandonados. |
| `REDIS_DEAD_LETTER_REPLAY_KEY` | `sentinel:stream:dead_letter:replayed` | Registro idempotente de replays DLQ. |
| `TELEMETRY_BATCH_SIZE` | `1000` | Tamaño de procesamiento configurado |
| `TELEMETRY_BUFFER_SIZE` | `10000` | Buffer configurado |
| `TELEMETRY_FLUSH_INTERVAL` | `5` | Intervalo en segundos |
| `RATE_LIMIT_REQUESTS` | `100` | Límite general |
| `RATE_LIMIT_PERIOD` | `60` | Periodo del límite en segundos |

El campo de configuración correcto es `ENVIRONMENT`. El nombre histórico `APP_ENVIRONMENT` del ejemplo general no debe usarse para configurar el backend.

### Seguridad de configuración

- No subir `backend/.env` ni secretos reales al repositorio.
- Los secretos incluidos en Compose son únicamente de desarrollo.
- Cambiar `SECRET_KEY`, `JWT_SECRET_KEY` y contraseñas antes de cualquier despliegue.
- Usar HTTPS en cualquier entorno accesible fuera de localhost.
- El archivo raíz `.env.example` contiene variables futuras de AWS, OpenSearch, correo y AI; no significa que esas integraciones estén activas.

### Perfil `local-production`

El desarrollo normal conserva `backend/docker-compose.yml` con hot reload, herramientas Adminer/Redis Commander y secretos de ejemplo. Para validar un arranque más cercano a producción sin AWS y sin modificar ese stack, usa el Compose separado:

```powershell
Copy-Item backend\.env.local-production.example backend\.env.local-production
# Editar backend\.env.local-production y reemplazar todos los placeholders

docker compose --env-file backend\.env.local-production -f backend\docker-compose.local-production.yml config --quiet
docker compose --env-file backend\.env.local-production -f backend\docker-compose.local-production.yml up -d --build
```

Este perfil usa `ENVIRONMENT=local-production`, `DEBUG=false`, `API_RELOAD=false`, Redis con contraseña, secretos obligatorios, sin Swagger/ReDoc/OpenAPI, sin bind mount del código y ejecuta `alembic upgrade head` antes de iniciar Uvicorn. Utiliza volúmenes con nombres distintos a los del Compose de desarrollo: no borra ni modifica los datos existentes. Para detenerlo sin borrar datos:

```powershell
docker compose --env-file backend\.env.local-production -f backend\docker-compose.local-production.yml down
```

### Migraciones Alembic

Las tablas nuevas o existentes se gestionan con migraciones formales. La primera revisión es un baseline idempotente: completa sólo tablas ausentes. La segunda añade `jwtsession`, `token.scopes`, `token.revoked_at` y `token.replaced_by_id` de forma aditiva.

```powershell
docker exec sentinel-backend alembic upgrade head
docker exec sentinel-postgres psql -U sentinel -d sentinelmonitoria -tAc "SELECT version_num FROM alembic_version;"
```

La revisión vigente comprobada en la validación local es `20260723_0005 (head)`. La migración `0005` reconcilia el esquema de telemetry sin borrar datos; las revisiones anteriores se conservan como historial de Alembic.

`local` y `development` mantienen `create_all` como compatibilidad para el arranque actual; `local-production` no crea tablas automáticamente y depende del comando Alembic del contenedor. No uses `down -v` ni `start-local.ps1 -Clean` para aplicar migraciones.

## Autenticación local

El dashboard exige una sesión válida. El frontend guarda temporalmente el par de tokens en `localStorage` bajo la clave `sentinelmonitoria.session`.

### Registro

Desde la pantalla de acceso, elegir `Create account` e introducir:

| Campo | Ejemplo | Descripción |
|---|---|---|
| Full name | `Local Operator` | Nombre visible |
| Username | `operator` | Usuario único |
| Email | `operator@example.com` | Correo válido según `EmailStr` |
| Password | `S3ntinel!Local2026` | Reglas de complejidad |
| Organization | `Sentinel Local` | Nombre de la organización |
| Identificador de organización | `sentinel-local` | Identificador legible, antes llamado slug |

El UUID interno de la organización se genera automáticamente. El identificador visible solo acepta letras minúsculas, números y guiones.

La contraseña debe tener como mínimo 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial. Se recomienda mantenerla por debajo de 72 bytes por compatibilidad con bcrypt.

`EmailStr` puede rechazar dominios reservados como `sentinel.local`; para pruebas usar `example.com` u otro dominio aceptado.

### Endpoints de sesión

| Método | Ruta | Requiere Bearer | Función |
|---|---|---:|---|
| `POST` | `/api/v1/auth/register` | No | Crea usuario, organización inicial y tokens |
| `POST` | `/api/v1/auth/login` | No | Login con username o email |
| `POST` | `/api/v1/auth/refresh` | No | Rota access y refresh token |
| `GET` | `/api/v1/auth/me` | Sí | Devuelve usuario y organizaciones |
| `POST` | `/api/v1/auth/logout` | Sí | Revoca las sesiones JWT del usuario y el cliente elimina sus tokens |
| `POST` | `/api/v1/auth/change-password` | Sí | Cambia la contraseña |

El logout revoca las sesiones JWT persistidas del usuario. El refresh token se consume al rotarse: reutilizar el valor anterior devuelve `401`. Un cambio de contraseña revoca las sesiones existentes y obliga a iniciar una nueva sesión.

## API keys y conexión de agentes

El dashboard incluye `Connections`, donde el usuario puede:

1. Ver la organización activa.
2. Crear una API key con nombre y expiración de 7, 30, 90, 365 días o sin expiración.
3. Copiar la key, que se muestra una sola vez.
4. Ver metadata de keys activas sin revelar el secreto.
5. Revocar una key.
6. Usar el endpoint de telemetry mostrado automáticamente.

El endpoint local es:

```text
POST http://localhost:8000/api/v1/telemetry
```

Endpoints de API keys:

| Método | Ruta | Función |
|---|---|---|
| `POST` | `/api/v1/auth/api-keys` | Genera y almacena una API key asociada a una organización |
| `POST` | `/api/v1/auth/api-keys/{token_id}/rotate` | Genera una replacement key y revoca inmediatamente la anterior |
| `DELETE` | `/api/v1/auth/api-keys/{token_id}` | Revoca una key propia |

El valor usable de las nuevas API keys no se almacena en PostgreSQL: se guarda un digest SHA-256 y la key completa se devuelve una sola vez. Las keys creadas antes de este endurecimiento siguen siendo compatibles; en el entorno local se migran automáticamente durante el arranque y el validador también puede migrar una fila legacy al primer uso. La lista nunca devuelve los valores completos y nunca se imprimen keys en logs. Antes de producción se recomienda usar además un gestor de secretos y una política de rotación.

Las API keys aceptan scopes explícitos: `telemetry:write` (por defecto y necesario para ingesta) y `telemetry:read` (reservado para lecturas futuras). Una key sólo con `telemetry:read` recibe `403` al intentar ingerir datos. La rotación crea una nueva key, conserva organización/límites/scopes salvo overrides y revoca inmediatamente la anterior; la transición no deja dos secretos activos.


### Ejemplo de conexión

Después de generar una key desde `Connections`:

```powershell
$base = "http://localhost:8000"
$apiKey = "API_KEY_COPIADA_UNA_SOLA_VEZ"

$headers = @{
  Authorization = "Bearer $apiKey"
  "Content-Type" = "application/json"
}

$payload = @{
  metadata = @{
    agent_id = "agent-local-001"
    hostname = "localhost"
    agent_version = "1.0.0"
    platform = "windows"
    architecture = "x64"
    tags = @{ environment = "local" }
  }
  metrics = @(
    @{
      name = "system.cpu.usage"
      value = 42.5
      type = "gauge"
      unit = "percent"
      labels = @{}
    }
  )
  logs = @()
  events = @()
  batch_id = "local-batch-001"
} | ConvertTo-Json -Depth 8

Invoke-RestMethod -Uri "$base/api/v1/telemetry" -Method Post -Headers $headers -Body $payload
```

Una key debe tener `organization_id` para ingerir telemetry. El backend valida firma JWT, tipo `api_key`, existencia, estado activo, expiración, usuario y organización.

## Contrato de telemetry

`POST /api/v1/telemetry` recibe un batch JSON con:

- `metadata` obligatorio:
  - `agent_id` obligatorio.
  - `hostname` obligatorio.
  - `agent_version` obligatorio.
  - `timestamp`, `platform`, `architecture` y `tags` opcionales.
- `metrics`, `logs` y `events`, todos opcionales individualmente, pero al menos uno debe contener datos.
- `batch_id` opcional para identificación/deduplicación.

Límites de validación:

- Máximo total: 10.000 items.
- Máximo metrics: 5.000.
- Máximo logs: 5.000.
- Máximo events: 1.000.

Ejemplo mínimo:

```json
{
  "metadata": {
    "agent_id": "agent-local-001",
    "hostname": "localhost",
    "agent_version": "1.0.0",
    "platform": "windows",
    "architecture": "x64",
    "tags": {"environment": "local"}
  },
  "metrics": [
    {
      "name": "system.cpu.usage",
      "value": 42.5,
      "type": "gauge",
      "labels": {},
      "unit": "percent"
    }
  ],
  "logs": [],
  "events": [],
  "batch_id": "local-batch-001"
}
```

Tipos de metricas: `gauge`, `counter`, `histogram`, `summary`, `untyped`.

Niveles de log: `debug`, `info`, `warning`, `error`, `fatal`, `trace`.

Severidades de evento: `info`, `low`, `medium`, `high`, `critical`.

## Catálogo de API

### Rutas raíz

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Información de aplicación, versión, docs y health |
| `GET` | `/health` | Health resumido de DB, Redis y telemetry |
| `GET` | `/metrics` | Métricas en formato Prometheus |
| `GET` | `/dev/stats` | Estadísticas de desarrollo |
| `POST` | `/dev/reset` | Borra y recrea tablas, Redis y colas; solo desarrollo |
| `GET` | `/dev/test-auth` | Token de prueba; solo desarrollo |

### Health v1

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/health` | Health detallado de API, DB, Redis, telemetry y recursos |
| `GET` | `/api/v1/health/liveness` | Comprueba que el proceso responde |
| `GET` | `/api/v1/health/readiness` | Comprueba dependencias listas |
| `GET` | `/api/v1/health/detailed` | Estadísticas profundas y conteos de tablas |
| `GET` | `/api/v1/health/history` | Historial simulado de health |
| `GET` | `/api/v1/health/dev/simulate-failure` | Simula fallo en desarrollo |
| `POST` | `/api/v1/health/dev/reset-health` | Reinicia datos simulados de health |

### Telemetry v1

| Método | Ruta | Auth | Descripción |
|---|---|---:|---|
| `POST` | `/api/v1/telemetry` | API key | Ingesta un batch y devuelve `202` |
| `GET` | `/api/v1/telemetry/health` | No | Health del servicio telemetry |
| `GET` | `/api/v1/telemetry/stats` | No | Estadísticas de procesamiento |
| `GET` | `/api/v1/telemetry/queues` | Sí | Profundidad de colas |
| `GET` | `/api/v1/telemetry/dead-letter` | Sí | Inspecciona fallos retenidos en Redis |
| `POST` | `/api/v1/telemetry/dead-letter/{stream_id}/replay` | Sí | Reencola una entrada DLQ una sola vez |
| `POST` | `/api/v1/telemetry/test` | No, dev | Valida una carga simulada sin ingesta real |
| `POST` | `/api/v1/telemetry/dev/reset-queues` | No, dev | Limpia colas mock |
| `POST` | `/api/v1/telemetry/dev/simulate-load` | No, dev | Simula hasta 1.000 batches |

### Documentación interactiva

Con `DEBUG=true` o `ENVIRONMENT=development`:

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

En producción estas rutas pueden estar deshabilitadas por configuración de FastAPI.

### Formato de errores

Los errores HTTP de la aplicación suelen responder:

```json
{
  "status": "error",
  "message": "Descripción del error",
  "path": "/api/v1/auth/login"
}
```

Los errores de validación incluyen un arreglo `errors` y normalmente responden `422`.

## Frontend

El frontend utiliza React 18.3.1 y Vite 8.1.5, sin framework UI adicional.

Scripts disponibles desde `frontend`:

```powershell
npm ci            # Instalar dependencias fijadas por package-lock.json
npm run dev       # Servidor local en localhost:3000
npm run build     # Build de producción en frontend/dist
npm run preview   # Servir el build local
```

El dashboard:

- Restaurará la sesión almacenada y comprobará `/auth/me`.
- Intentará refresh si el access token expira.
- Redirigirá al login si no existe una sesión válida.
- Consume `/health`, `/api/v1/telemetry/health`, `/api/v1/telemetry/stats` y `/metrics`.
- Actualiza señales automáticamente cada 30 segundos.
- Muestra estado de PostgreSQL, Redis, telemetry y las colas del proveedor activo.
- Permite generar y revocar API keys desde `Connections`.

## Docker Compose

El archivo principal es `backend/docker-compose.yml` y contiene:

- `postgres`: `postgres:15-alpine`.
- `redis`: `redis:7-alpine` sin password local.
- `backend`: imagen propia, hot reload y volumen del código.
- `adminer`: interfaz PostgreSQL.
- `redis-commander`: interfaz Redis.
- `localstack`: perfil opcional `aws`, no iniciado por defecto.

Para activar el flujo durable local sin cambiar el comportamiento predeterminado ni eliminar volúmenes:

```powershell
docker compose -f backend\docker-compose.yml -f backend\docker-compose.redis-worker.yml config --quiet
docker compose -f backend\docker-compose.yml -f backend\docker-compose.redis-worker.yml up -d --build backend worker
docker compose -f backend\docker-compose.yml -f backend\docker-compose.redis-worker.yml ps
```

El override define `sentinel-worker`, usa `QUEUE_PROVIDER=redis`, publica en `sentinel:stream:<queue>`, consume telemetry mediante el grupo `sentinel-telemetry-workers` y envía fallos agotados a `sentinel:stream:dead_letter`. Verifica el flujo con `GET /health`, `GET /api/v1/telemetry/health` y `XPENDING`; `docker compose down` conserva datos y no debe sustituirse por `down -v`.

El override opcional `backend/docker-compose.frontend.yml` añade `sentinel-frontend`, construye una imagen Node autocontenida con `npm ci` y conserva `VITE_API_BASE_URL=http://localhost:8000` para que el navegador llegue al backend desde Windows. Después de cambiar el frontend, reconstruye con `--build`. Puede activarse con `-Frontend` en `start-local.ps1` o con los comandos directos de la sección de frontend.

LocalStack puede requerir `LOCALSTACK_AUTH_TOKEN` y no forma parte del flujo validado. No activar el perfil `aws` para el desarrollo normal.

## Agente Vector

`agent/` contiene una configuración Vector `0.36.0` para Linux:

- Fuentes de host metrics, journald, archivos y logs Docker.
- Transformaciones VRL y envelopes compatibles con `TelemetryBatchSchema`.
- Buffer en disco de 1 GiB con política `block` para evitar pérdida por saturación.
- Sink HTTP newline-delimited hacia `/api/v1/telemetry`.
- Métricas locales en `:9598/metrics`.
- Dockerfile y scripts de instalación para Linux.

La configuración normal pasa `vector validate` después de expandir sus variables de entorno. La ejecución de journald, archivos y Docker debe validarse en un host Linux con los permisos y montajes correspondientes. El flujo E2E reproducible para Windows + Docker está separado en `agent/deploy/docker-compose.e2e.yml`. El Compose auxiliar `agent/deploy/docker-compose.yml` también define Prometheus, Grafana y un mock API; no debe ejecutarse al mismo tiempo que el stack principal sin revisar conflictos de puertos.

## Scripts operativos

| Script | Uso |
|---|---|
| `scripts/check-docker.ps1` | Comprueba Docker Desktop, Compose, daemon, WSL y hello-world |
| `scripts/start-local.ps1` | Inicia, reconstruye, sigue logs o limpia el stack local; `-Frontend` añade Vite y `-Intelligence` añade Redis Streams, AI worker y notification worker |
| `scripts/test-local.ps1` | Smoke check read-only de backend, observabilidad y frontend opcional |
| `scripts/test-api.ps1` | Smoke test de endpoints públicos y development |
| `scripts/aws-preflight.ps1` | Comprueba identidad, cuenta, región, zonas e IAM esperado cuando se ejecuta explícitamente |
| `scripts/validate-cloudformation.ps1` | Valida CloudFormation base `00–14` o, con `-IncludeAiNotifications`, también `19–22` |
| `scripts/deploy-cloudformation-phases.ps1` | Despliega stacks base y fases IA/notificaciones opcionales mediante Change Sets y parámetros |
| `scripts/build-push-ecr.ps1` | Construye y publica imágenes ECR `linux/arm64` con tags inmutables |
| `scripts/run-aws-migration.ps1` | Ejecuta Alembic en una tarea ECS one-off antes de activar servicios |
| `scripts/publish-frontend.ps1` | Construye React/Vite contra el ALB, publica `frontend/dist` en el S3 Website activo y valida la configuración Website antes de terminar. |
| `scripts/check-system.ps1` | Comprobación general antigua; puede requerir `docker-compose` legacy |
| `scripts/build-agent.sh` | Construye imagen y paquetes del agente en Linux con Docker, dpkg y rpmbuild |

Uso de `start-local.ps1`:

```powershell
.\scripts\start-local.ps1          # iniciar backend y servicios
.\scripts\start-local.ps1 -Build   # construir e iniciar backend y servicios
.\scripts\start-local.ps1 -Frontend # añadir frontend Docker en localhost:3000
.\scripts\start-local.ps1 -Intelligence # añadir Redis Streams, AI worker y notification worker
.\scripts\start-local.ps1 -Build -Frontend # construir e iniciar todo
.\scripts\start-local.ps1 -Build -Intelligence # construir e iniciar análisis IA y alertas
.\scripts\start-local.ps1 -Logs    # iniciar y seguir logs
.\scripts\start-local.ps1 -Clean   # borrar volúmenes locales
```

Smoke check read-only:

```powershell
.\scripts\test-local.ps1
.\scripts\test-local.ps1 -RequireFrontend
```

## Validación

Comprobación básica:

```powershell
.\scripts\check-docker.ps1
.\scripts\start-local.ps1

docker compose -f backend\docker-compose.yml ps
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/health
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/stats
Invoke-WebRequest http://localhost:3000/ -UseBasicParsing
```

Smoke check local:

```powershell
.\scripts\test-local.ps1 -RequireFrontend
```

Build frontend:

```powershell
Set-Location frontend
npm run build
```

Pruebas automatizadas del backend:

```powershell
# Con Docker Compose levantado
Set-Location backend
docker exec sentinel-backend pytest -q
```

La suite actual usa `pytest`, `pytest-asyncio` y `httpx` contra el stack local. Comprueba:

- Hash de API keys sin almacenar el secreto usable.
- Registro, login, refresh y `/auth/me`.
- Creación y listado de API keys sin exponer `token`.
- Ingesta telemetry con respuesta `202`.
- Compatibilidad y migración de una API key legacy almacenada en texto.
- Revocación y rechazo posterior con `401`.

La suite validada actualmente contiene 19 pruebas correctas y 1 omitida porque el stack predeterminado usa `QUEUE_PROVIDER=mock`; la prueba omitida requiere Redis Streams y el worker persistente. El frontend tiene 9/9 pruebas correctas, el smoke API tiene 9/9 comprobaciones y `scripts/test-local.ps1 -RequireFrontend` se validó con 8/8 comprobaciones. Crea datos de prueba con identificadores únicos y no ejecuta `down -v` ni borra los volúmenes locales.

La infraestructura declarativa se comprobó offline mediante parseo de 23 templates YAML, matriz JSON, sintaxis PowerShell, contratos `19`–`22`, Redis TLS y `git diff --check`. Además, el staging activo se validó con llamadas reales a S3, ALB, ECS, RDS/Redis vía health, Lex V2 y telemetry. Las comprobaciones offline no sustituyen la ejecución de Change Sets ni prueban los componentes bloqueados —CloudFront, HTTPS y Bedrock— hasta que la cuenta los autorice.

Flujo de autenticación recomendado:

1. Registrar usuario.
2. Confirmar `/api/v1/auth/me` con el access token.
3. Crear API key con `organization_id`.
4. Enviar un batch válido a `/api/v1/telemetry`.
5. Consultar `/api/v1/telemetry/stats`.
6. Revocar la key.
7. Confirmar que una nueva ingesta con esa key falla.

La validación local realizada confirmó:

- Backend y telemetry saludables.
- Build frontend correcto y frontend respondiendo HTTP 200.
- Registro, login por email, `/me`, refresh y logout.
- Creación de API key asociada a una organización.
- Listado de API keys sin exponer el campo `token`.
- Ingesta real de telemetry con API key y respuesta HTTP 202.
- Revocación de API key con respuesta HTTP 200.
- Rechazo posterior de la key revocada con HTTP 401.
- Compatibilidad de fechas timezone-aware durante la validación.
- Respuestas de error de telemetry serializadas correctamente.
- Echo SQL desactivado para evitar que parámetros sensibles aparezcan en logs.

### Correcciones finales de estabilidad y seguridad

Durante la última validación local se corrigieron estos problemas:

- **`GET /health` devolvía `500`:** la respuesta incluía fechas `datetime` sin convertir. Ahora el endpoint usa `jsonable_encoder`, por lo que responde correctamente con `status=healthy` cuando PostgreSQL, Redis y telemetry están disponibles.
- **Telemetry devolvía `500` al recibir fechas:** el cálculo del tamaño del batch y el mensaje enviado a la cola mock conservaban objetos `datetime`. Ambos caminos convierten ahora el batch a JSON antes de serializarlo.
- **Logs de autenticación:** se eliminó el registro de fragmentos del Bearer token. Los errores de autenticación registran contexto operativo, pero no imprimen JWTs ni API keys.
- **SQL sensible:** `echo` de SQL permanece desactivado para impedir que los valores de parámetros aparezcan en la salida del backend.

La corrección de serialización aplica al flujo local con `QUEUE_PROVIDER=mock` y también deja el payload preparado para proveedores de cola que serialicen JSON. No sustituye el endurecimiento productivo: las API keys todavía deben migrarse a hash o cifrado con un gestor de secretos antes de producción.

### Evidencia de validación final

La validación posterior a la reconstrucción y recreación del contenedor `backend` confirmó:

| Comprobación | Resultado esperado | Resultado validado |
|---|---:|---:|
| `GET /health` | `healthy` | Correcto |
| `GET /api/v1/telemetry/health` | `healthy` | Correcto |
| Ingesta con API key activa | HTTP `202` | Correcto |
| Revocación de API key | HTTP `200` | Correcto |
| Ingesta con key revocada | HTTP `401` | Correcto |
| Listado de keys | No incluir `token` | Correcto |
| Logs recientes | Sin JWT-like values ni errores fatales | Correcto |
| Compilación backend | `compileall` sin errores | Correcto |
| Build frontend | Vite build exitoso | Correcto |

Para comprobar los logs sin exponer su contenido completo:

```powershell
$logs = docker logs --since=30s sentinel-backend 2>&1 | Out-String
[regex]::IsMatch($logs, '(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])')
```

El resultado esperado es `False`. Un `401` después de revocar una API key es un resultado correcto de seguridad, no un fallo del servicio.

## Troubleshooting

### Docker no aparece en PATH

```powershell
$env:Path = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;$env:Path"
docker --version
docker compose version
```

Abrir Docker Desktop y esperar a que indique que el engine está ejecutándose.

### El backend no inicia

```powershell
docker compose -f backend\docker-compose.yml logs --tail=200 backend
docker compose -f backend\docker-compose.yml ps
```

Después de cambiar `requirements.txt`, reconstruir:

```powershell
docker compose -f backend\docker-compose.yml up -d --build backend
```

La combinación usada para hashing local es `passlib==1.7.4` con `bcrypt==4.0.1`. No actualizar bcrypt sin validar compatibilidad.

### El frontend muestra API desconectada

Comprobar:

```powershell
Invoke-RestMethod http://localhost:8000/health
$env:VITE_API_BASE_URL
```

Verificar que el navegador esté en `http://localhost:3000` o que el origen esté incluido en `API_CORS_ORIGINS`.

### La API key devuelve 401

- Confirmar que se copió completa al momento de generarla.
- Confirmar que la key no fue revocada ni expiró.
- Confirmar que fue creada con una organización.
- Usar `Authorization: Bearer <key>`.
- Verificar que el backend reconstruido tenga la versión actual del código.
- Revisar logs sin imprimir el token.

### La ingesta devuelve 400 por organización

La API key debe incluir `organization_id`. Generarla desde `Connections`, donde el sistema usa la organización asociada al usuario.

### Error de correo durante registro

Usar un dominio aceptado por `EmailStr`, por ejemplo `operator@example.com`. Dominios reservados como `sentinel.local` pueden ser rechazados.

### Restablecer datos locales

Advertencia: esto elimina usuarios, organizaciones, tokens y telemetry:

```powershell
.\scripts\start-local.ps1 -Clean
.\scripts\start-local.ps1 -Build
```

### LocalStack

No activarlo para la prueba normal. Si se necesita explorar el perfil AWS:

```powershell
docker compose --profile aws -f backend\docker-compose.yml up -d localstack
```

Puede requerir configuración adicional de LocalStack y no cambia `QUEUE_PROVIDER=mock` automáticamente.

## Seguridad y límites actuales

Esta configuración es para desarrollo local:

- Las sesiones JWT se persisten por `jti`; logout y cambio de contraseña revocan sesiones, y refresh consume el token anterior para impedir replay.
- Las API keys nuevas se almacenan como digest SHA-256, admiten scopes y rotación explícita; las filas legacy se migran sin invalidarlas automáticamente.
- `local-production` exige secretos no predeterminados, `DEBUG=false`, `API_RELOAD=false` y Redis con contraseña, pero sigue siendo un entorno local sin AWS real.
- El Compose de desarrollo conserva secretos de ejemplo, CORS localhost, Redis sin password y herramientas de administración; no debe exponerse fuera de localhost.

## Roadmap

Prioridad recomendada después de la evaluación:

1. Mantener monitorizado el staging desplegado: health del ALB, tareas ECS, RDS, Redis, productor EC2, logs y presupuesto.
2. Rotar o revocar las credenciales de demostración y detener recursos temporales cuando finalice la ventana del jurado.
3. Completar la verificación de la cuenta AWS nueva para desbloquear CloudFront y revisar nuevamente el acceso a modelos Bedrock.
4. Promover el borde a S3 privado + CloudFront/OAC y habilitar Route 53, ACM y HTTPS mediante las fases `14`–`18`.
5. Mantener Lex V2 y el AI worker con fallback determinístico hasta que Nova/Titan aparezcan `AUTHORIZED`; después ejecutar una prueba comparativa en español antes de habilitar Bedrock o RAG.
6. Activar Knowledge Base/S3 Vectors únicamente con corpus redactado, presupuesto, métricas de relevancia y aprobación explícita.
7. Diseñar la alta disponibilidad productiva: NAT por AZ o NAT Gateway, RDS Multi-AZ, Redis con failover, autoscaling ECS, WAF, backups y pruebas de restauración.
8. Activar notificaciones externas sólo con secretos gestionados, destinos aprobados, reintentos, DLQ y auditoría; conservar `AI_ENABLE_ACTIONS=false` hasta disponer de aprobación y rollback.
9. Incorporar CI/CD para validar tests, templates CloudFormation, imágenes ARM64, migraciones Alembic, despliegues progresivos y rollback.
10. Continuar la validación local y del agente Vector en Linux para mantener una ruta reproducible independiente del entorno AWS.

## Manual ejecutivo y documentación adicional

El manual ejecutivo reúne el flujo completo para instalar, levantar, utilizar, validar y detener SentinelMonitorIA en Windows con Docker Desktop. Incluye una edición PDF lista para distribución y sus fuentes reproducibles offline:

- [Manual ejecutivo en PDF](docs/manual/SentinelMonitorIA-Manual-Ejecutivo.pdf)
- [Fuente Markdown editable](docs/manual/SentinelMonitorIA-Manual-Ejecutivo.md)
- [Fuente HTML/CSS para impresión](docs/manual/SentinelMonitorIA-Manual-Ejecutivo.html)
- [Script reproducible de generación PDF](scripts/build-manual-pdf.ps1)

Para regenerar el PDF con Google Chrome instalado:

```powershell
.\scripts\build-manual-pdf.ps1
```

- [Arquitectura del agente](docs/architecture/agent-architecture.md)
- [Guía del backend](backend/README.md)
- [Guía del agente](agent/README.md)
- [Variables generales](.env.example)
- [Variables backend](backend/.env.example)
- [Compose local](backend/docker-compose.yml)
- [Compose local-production](backend/docker-compose.local-production.yml)
- [Ejemplo de entorno local-production](backend/.env.local-production.example)
- [Runbook local y preproducción](docs/operations/local-runbook.md)
- [Informe de validación local](docs/operations/local-validation-report.md)
- [Plan CloudFormation offline](docs/deployment/cloudformation-plan.md)
- [Foundation CloudFormation](infra/cloudformation/README.md)
- [Configuración Alembic](backend/alembic.ini)
- [Licencia](LICENSE)

## Licencia

Apache 2.0. Ver [LICENSE](LICENSE).

## Equipo y reconocimiento

<p align="center">
  <strong>Construido para demostrar que una plataforma AIOps segura, explicable y reproducible puede pasar del repositorio a AWS con evidencia operativa real.</strong>
</p>

Este proyecto ha sido realizado por un equipo latinoamericano para la evaluación de AWS y Código Facilito:

<table>
  <tr>
    <th>Bandera</th>
    <th>Integrante</th>
    <th>País</th>
    <th>Contacto</th>
  </tr>
  <tr>
    <td><img src="Imagenes/peru.png" alt="Bandera de Perú" width="42" height="42"></td>
    <td>Jeffersson Pretell Velasquez</td>
    <td>Perú</td>
    <td><a href="mailto:jpretelll66@gmail.com">jpretelll66@gmail.com</a></td>
  </tr>
  <tr>
    <td><img src="Imagenes/peru.png" alt="Bandera de Perú" width="42" height="42"></td>
    <td>Fernanda Flórez Hereña</td>
    <td>Perú</td>
    <td><a href="mailto:fernandaflorezherena@gmail.com">fernandaflorezherena@gmail.com</a></td>
  </tr>
  <tr>
    <td><img src="Imagenes/bandeira-venezuela-flag-0.png" alt="Bandera de Venezuela" width="42" height="42"></td>
    <td>Jose Jose Ramones Moreno</td>
    <td>Venezuela</td>
    <td><a href="mailto:ramonesj@gmail.com">ramonesj@gmail.com</a></td>
  </tr>
</table>

**Última actualización:** 26 de julio de 2026, 21:46 (UTC-05:00)<br>
**Cuenta AWS:** nueva, activada el 25 de julio de 2026; MVP desplegado en `us-east-1`<br>
**Copyright © 2026 SentinelMonitorIA.** Todos los derechos reservados.<br>
Distribuido bajo la [Licencia Apache 2.0](LICENSE).
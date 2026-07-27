# SentinelMonitorIA
## Guion del video para el jurado

**Duración objetivo:** 5 minutos<br>
**Audiencia:** jurado AWS y Código Facilito<br>
**Entorno:** AWS staging, Lex V2, productor sintético EC2<br>
**Objetivo:** demostrar el flujo en vivo desde telemetry hasta una alerta visible, junto con el chat estructurado.

> Durante la grabación no mostrar la contraseña ni la API key. Usar las credenciales del dossier sólo para iniciar sesión o para la preparación previa.

## Preparación antes de grabar

- Abrir el frontend S3 Website HTTP, no Amplify.
- Hacer `Ctrl+F5`.
- Confirmar que `/health` y `/api/v1/telemetry/health` devuelven `200`.
- Confirmar que `sentinel-mvp-demo-producer.service` está `active`.
- Tener al menos una alerta sintética visible.
- Ocultar valores secretos en capturas o consola.
- Tener preparada la vista del dashboard y el chat.

## 0:00–0:25 — Presentación

### Acción en pantalla

Mostrar la portada o el dashboard de SentinelMonitorIA.

### Texto hablado

> “Hola. En este video presentaré SentinelMonitorIA, una plataforma de observabilidad y AIOps orientada a detectar señales operativas, analizarlas y generar alertas de forma controlada.
>
> La demostración utiliza datos sintéticos, una cuenta demo y una fuente de telemetry controlada. No se utilizan datos reales ni se ejecutan acciones automáticas sobre la infraestructura.”

## 0:25–0:55 — Arquitectura AWS

### Acción en pantalla

Mostrar el dashboard y, si el tiempo lo permite, abrir `/health`.

### Texto hablado

> “El frontend React está publicado en un S3 Website y se comunica con un Application Load Balancer. El ALB dirige las solicitudes al backend FastAPI desplegado en ECS.
>
> El backend utiliza PostgreSQL para persistencia y Redis Streams para procesar los eventos de forma asíncrona. Sobre esta base funcionan el worker de telemetry, el worker de análisis y el sistema de alertas.”

## 0:55–1:25 — Autenticación y estado operativo

### Acción en pantalla

Mostrar la sesión iniciada y el panel de servicios.

### Texto hablado

> “La cuenta utilizada en esta demostración es una cuenta de aplicación independiente de AWS. La autenticación del usuario se realiza mediante JWT y la información está aislada dentro de su organización.
>
> La API key del agente sintético es independiente del token de sesión del usuario y sólo tiene permiso para escribir telemetry. Por seguridad, no mostraremos el secreto en pantalla.”

## 1:25–2:10 — Lex V2 y conversación estructurada

### Acción en pantalla

Abrir el chat **Ask Sentinel**. Escribir:

```text
¿Cuántas alertas abiertas hay?
```

Después escribir:

```text
Resume las alertas críticas.
```

Mostrar el footer del chat.

### Texto hablado

> “El asistente conversacional utiliza Amazon Lex V2 para interpretar las solicitudes del usuario.
>
> Lex identifica intenciones como consultar alertas abiertas, revisar telemetry, consultar alertas críticas o pedir ayuda. También puede validar los datos requeridos mediante slots y entregar al backend una solicitud estructurada.
>
> En este proyecto Lex V2 se utiliza sin Bedrock y sin embeddings. Lex realiza el reconocimiento de intención y el flujo conversacional; la respuesta operativa se produce mediante reglas determinísticas del backend.”

### Frase de apoyo

> “La prueba de consulta de alertas resuelve `OpenAlertsIntent` en el locale `es_419`. La respuesta queda limitada a la organización autenticada y no ejecuta acciones automáticas.”

## 2:10–2:55 — Productor sintético en la EC2

### Acción en pantalla

Mostrar la instancia `test-redes` o una diapositiva con su estado. No mostrar el archivo de credenciales.

### Texto hablado

> “Para demostrar el funcionamiento en vivo se creó un productor sintético separado en la instancia EC2 existente `test-redes`, una `t3.micro` con Amazon Linux 2023.
>
> El productor se ejecuta como un servicio systemd con un usuario no root, sin abrir puertos adicionales y con límites de CPU y memoria.
>
> Cada 30 a 60 segundos envía telemetry normal. Cada 5 a 10 minutos genera un incidente controlado. Los valores altos son datos sintéticos del payload; no generan carga real sobre la EC2.”

### Datos que se pueden mencionar

- Agent ID: `ec2-test-redes-synthetic`.
- Tags: `environment=mvp-demo`, `synthetic=true`, `source=continuous-demo`.
- Servicio: `sentinel-mvp-demo-producer.service`.

## 2:55–3:45 — Incidente y generación de alerta

### Acción en pantalla

Actualizar la vista de alertas y abrir una alerta reciente.

### Texto hablado

> “El incidente sintético contiene una métrica de CPU de 96%, una métrica de memoria de 94%, un log con nivel `error` y un evento con severidad `high`.
>
> El backend recibe el batch con HTTP 202 y lo procesa de forma asíncrona. El worker de telemetry persiste los datos y los envía al análisis de inteligencia.
>
> El detector identifica que CPU y memoria superan el umbral del 90%. El resultado se almacena como `AIAnalysis` y posteriormente se crea una alerta `high`.”

### Elementos a señalar

- Severidad `high`.
- Regla `metric.cpu.high`.
- Agent ID sintético.
- Evidencia del análisis.
- `analysis_id` asociado a la alerta.

### Frase de transición

> “Aquí podemos observar el flujo completo: telemetry, análisis y alerta.”

## 3:45–4:25 — Servicios y notificaciones controladas

### Acción en pantalla

Mostrar, desde el dashboard o documentación, los servicios ECS y el estado de las colas.

### Texto hablado

> “El backend, el worker de telemetry y el AI worker están activos. El notification worker permanece apagado intencionalmente.
>
> Esto permite demostrar la generación y visualización de alertas sin enviar correos, mensajes a Slack, Discord, Teams ni webhooks externos.
>
> También se mantienen deshabilitadas las acciones automáticas mediante `AI_ENABLE_ACTIONS=false`. El sistema detecta y presenta señales, pero no ejecuta remediaciones.”

### Estados esperados

```text
backend:              1/1
telemetry worker:     1/1
AI worker:            1/1
notification worker:  0/0
notifications queue:  0
```

## 4:25–4:50 — Seguridad y coste

### Acción en pantalla

Mostrar la vista de servicios o una diapositiva de controles.

### Texto hablado

> “La demostración reutiliza una EC2 que ya estaba encendida, por lo que no fue necesario crear un servicio ECS adicional para el productor.
>
> El agente se ejecuta con un usuario no root, límites de CPU y memoria, archivo de credenciales protegido y sin puertos de entrada nuevos.
>
> RDS y Redis mantienen su infraestructura sin cambios. Sólo se persisten los datos sintéticos necesarios para demostrar el flujo del MVP.”

## 4:50–5:00 — Cierre

### Acción en pantalla

Volver al dashboard con una alerta visible y el footer Lex V2.

### Texto hablado

> “En resumen, SentinelMonitorIA recibe telemetry, la procesa de forma asíncrona, detecta anomalías, genera análisis y presenta alertas en el dashboard.
>
> Lex V2 proporciona el flujo conversacional estructurado sin Bedrock ni embeddings, mientras que el productor sintético mantiene una demostración continua, controlada y reproducible.
>
> El resultado es un MVP funcional que puede observarse en vivo sin activar notificaciones externas ni ejecutar acciones sobre la infraestructura.”

## Plan alternativo si no aparece una alerta

Antes de iniciar la grabación:

1. Confirmar que el servicio systemd está activo.
2. Confirmar `/health` y `/api/v1/telemetry/health`.
3. Actualizar el dashboard.
4. Si se necesita una alerta inmediata, ejecutar previamente el smoke incident controlado mediante SSM.
5. No ejecutar comandos de instalación durante la grabación.

Si el chat responde `401`:

1. Confirmar que se está usando el S3 Website HTTP.
2. Hacer `Ctrl+F5`.
3. Cerrar sesión y autenticarse de nuevo.
4. Si persiste, limpiar `localStorage` con:

```javascript
localStorage.removeItem("sentinelmonitoria.session");
location.reload();
```

La API key de telemetry no debe utilizarse como token del chat.

## Mensaje final opcional

> “La demostración no muestra datos simulados aislados: muestra un flujo operativo completo y persistente, desde la fuente de telemetry hasta la alerta visible en el sistema.”

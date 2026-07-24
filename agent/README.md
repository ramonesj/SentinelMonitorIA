# SentinelMonitorIA Agent

Agente de telemetría basado en Vector para recolectar métricas del host, logs y métricas Docker. El código y la configuración están preparados para una futura distribución Linux, pero el agente todavía no forma parte del flujo validado del Compose principal.

La guía general del proyecto está en [../README.md](../README.md).

## Estado actual

Disponible en el repositorio:

- `Dockerfile` basado en Vector compilado desde fuente.
- Configuración `configs/vector.toml`.
- Fuentes `host_metrics`, journald, archivos y Docker.
- Transformaciones VRL para logs, métricas y Docker.
- Buffer de disco configurado a 1 GB.
- Sink HTTP hacia `/api/v1/telemetry`.
- Endpoint de métricas local en `:9598/metrics`.
- Instalador Linux con systemd en `deploy/install.sh`.
- Healthcheck y entrypoint dinámico.
- Compose auxiliar con agente, Prometheus, Grafana y mock API.

Estado validado localmente:

- `Dockerfile.e2e` basado en Vector oficial `0.36.0-alpine` para una build reproducible del E2E.
- `configs/vector.e2e.toml` convierte fixture JSONL en batches compatibles con `TelemetryBatchSchema`.
- API key persistida asociada a organización y con scope `telemetry:write` validada.
- Networking validado mediante `backend_sentinel-network` y `http://backend:8000`.
- Pipeline real validado hasta Redis Streams, worker y PostgreSQL.
- El Compose auxiliar normal sigue separado y no forma parte del arranque principal.

Pendiente antes de usarlo como integración oficial de producción:

- Validar las fuentes host/journald/Docker del `configs/vector.toml` en un host Linux real.
- Integrar el agente en el pipeline de CI/CD.
- Revisar el despliegue Linux y secretos para un entorno no local.

## Flujo de datos

```text
Host metrics / journald / files / Docker
                  │
                  ▼
             Vector sources
                  │
                  ▼
             VRL transforms
                  │
                  ▼
          Disk buffer de 1 GB
                  │
                  ▼
 POST /api/v1/telemetry con Bearer API key
                  │
                  ▼
        SentinelMonitorIA Backend
```

## Archivos principales

```text
agent/
├── configs/vector.toml          # Fuentes, transforms, buffer y sinks
├── configs/vector.e2e.toml      # Pipeline E2E determinista con fixture JSONL
├── deploy/install.sh            # Instalación Linux con systemd
├── deploy/entrypoint.sh         # Variables, envsubst y validación Vector
├── deploy/healthcheck.sh        # Health process/metrics
├── deploy/docker-compose.yml    # Stack auxiliar del agente
├── deploy/docker-compose.e2e.yml # Compose E2E contra el backend local
├── deploy/prometheus.yml        # Configuración Prometheus
├── fixtures/e2e-telemetry.jsonl # Métrica, log y evento de prueba
├── scripts/generate-e2e-fixture.ps1 # Regenera IDs únicos
├── Dockerfile
├── Dockerfile.e2e              # Imagen Vector 0.36.0 oficial para E2E local
└── README.md
```

## Variables del agente

| Variable | Requerida | Descripción |
|---|---:|---|
| `SENTINEL_API_KEY` | Sí | API key creada desde `Dashboard → Connections` |
| `SENTINEL_API_ENDPOINT` | No | Base URL, por defecto `https://api.sentinelmonitoria.com` |
| `SENTINEL_AGENT_VERSION` | No | Versión reportada |
| `SENTINEL_HOSTNAME` | No | Hostname; se genera si está vacío |
| `SENTINEL_AGENT_ID` | No | ID; se genera si está vacío |
| `VECTOR_LOG_LEVEL` | No | `info`, `debug`, `warn` o `error` |

La configuración usa la URL base y añade `/api/v1/telemetry`. Para desarrollo local, el endpoint conceptual es:

```text
http://localhost:8000/api/v1/telemetry
```

Dentro de otro contenedor, `localhost` apunta al propio agente. Debe utilizarse el nombre de servicio Docker o la dirección accesible del backend.

## Uso con Docker

El Compose auxiliar está en `agent/deploy/docker-compose.yml`. No ejecutarlo junto con el Compose backend/frontend sin modificar puertos: el stack auxiliar define un mock API en `8000` y Grafana en `3000`, que entran en conflicto con FastAPI y Vite.

Para inspeccionar la configuración sin iniciar todo el stack:

```bash
docker compose -f agent/deploy/docker-compose.yml config
```

El archivo contiene valores de desarrollo como `test-key`; debe reemplazarse por una API key real generada desde `Connections` antes de probar ingestión.

Ejemplo conceptual de ejecución independiente:

```bash
SENTINEL_API_KEY="API_KEY_GENERADA" \
SENTINEL_API_ENDPOINT="http://backend:8000" \
docker compose -f agent/deploy/docker-compose.yml up -d sentinel-agent
```

La red y el hostname `backend` deben existir en el entorno donde se ejecute el agente. Este comando no forma parte del inicio rápido Windows validado.

## Flujo E2E local en Windows + Docker

El flujo E2E aislado valida el agente Vector real, la API, Redis Streams, el worker y PostgreSQL sin AWS. Usa la red externa `backend_sentinel-network` y no inicia el mock API, Prometheus ni Grafana del Compose auxiliar.

Prerequisitos:

1. Tener levantados el backend y el worker con Redis:

```powershell
docker compose -f backend/docker-compose.yml -f backend/docker-compose.redis-worker.yml up -d
```

2. Crear una API key persistida con el scope `telemetry:write` y asignarla en PowerShell. No uses `test-key`:

```powershell
$env:SENTINEL_API_KEY = "API_KEY_REAL_CON_TELEMETRY_WRITE"
$env:SENTINEL_API_ENDPOINT = "http://backend:8000"
```

3. Regenerar el fixture para que cada ejecución tenga `batch_id` nuevos:

```powershell
pwsh -File agent/scripts/generate-e2e-fixture.ps1
```

4. Construir e iniciar únicamente el agente E2E:

```powershell
docker compose -f agent/deploy/docker-compose.e2e.yml up -d --build
```

El Compose E2E exige `SENTINEL_API_KEY`, conecta Vector a `http://backend:8000` por `backend_sentinel-network`, y monta `configs/vector.e2e.toml`. Cada línea del fixture se transforma en un batch válido con una métrica, un log o un evento. El puerto de métricas del agente, si se necesita, queda en `http://localhost:9599/metrics`.

Comprobaciones posteriores:

```powershell
docker compose -f agent/deploy/docker-compose.e2e.yml logs sentinel-agent-e2e
docker exec sentinel-redis redis-cli XPENDING sentinel:stream:telemetry sentinel-telemetry-workers
```

Para repetir sin colisiones, genera de nuevo el fixture y recrea el contenedor. No borres volúmenes ni uses `down -v`:

```powershell
pwsh -File agent/scripts/generate-e2e-fixture.ps1
docker compose -f agent/deploy/docker-compose.e2e.yml up -d --build --force-recreate
```

Resultado validado localmente:

- Vector `0.36.0` inició healthy y procesó las tres líneas del fixture.
- La API respondió `202 Accepted` para una métrica, un log y un evento.
- Redis Streams mantuvo el stream y el consumer group con `XPENDING=0` y `lag=0`.
- PostgreSQL persistió tres `TelemetryBatch` con estado `processed`, además de una fila en `metric`, `logentry` y `event` para cada tipo.
- El backend y `/api/v1/telemetry/health` respondieron `healthy`.

## Instalación Linux preparatoria

`deploy/install.sh` instala Vector `0.36.0`, crea el usuario `sentinel`, prepara:

```text
/etc/sentinelmonitoria/       # Configuración y .env
/var/lib/sentinelmonitoria/   # Datos
/var/log/sentinelmonitoria/   # Logs
/opt/sentinelmonitoria/bin/   # Utilidades
```

El instalador requiere root, systemd y dependencias como `curl`, `wget`, Docker y `jq`:

```bash
sudo bash deploy/install.sh
sudo /opt/sentinelmonitoria/bin/configure.sh
sudo systemctl status sentinel-agent
```

Antes de ejecutarlo en un servidor real, revisar URLs de descarga, versión de Vector, certificados, permisos del socket Docker y el secreto que se escribirá en `/etc/sentinelmonitoria/.env`.

## Configuración Vector

`configs/vector.toml` define:

### Sources

- `system_metrics`: CPU, memoria, disco, filesystem, red y procesos cada 10 segundos.
- `system_logs`: journald.
- `application_logs`: archivos bajo `/var/log`.
- `docker_metrics`: logs Docker.
- `docker_api`: métricas de Docker cada 30 segundos.

### Transforms

- Parseo y nivel de logs del sistema.
- Enriquecimiento de métricas con hostname y plataforma.
- Parseo de logs Docker.
- Buffer de disco con `max_size = 1073741824`.

### Sinks

- `sentinel_api`: HTTP JSON comprimido con Bearer token, retry y rate limit.
- `local_log`: consola para debugging.
- `local_metrics`: Prometheus en `127.0.0.1:9598`.

Validar una configuración en un host con Vector instalado:

```bash
vector validate /etc/sentinelmonitoria/vector.toml
curl http://localhost:9598/metrics
```

## Health y troubleshooting

```bash
sudo systemctl status sentinel-agent
sudo journalctl -u sentinel-agent -f
curl http://localhost:9598/metrics
vector validate /etc/sentinelmonitoria/vector.toml
docker ps
```

Problemas frecuentes:

- **API key 401:** comprobar que no fue revocada, que pertenece a una organización y que el endpoint apunta al backend correcto.
- **No hay métricas Docker:** montar `/var/run/docker.sock` en modo lectura y comprobar permisos.
- **No hay logs journald:** ejecutar en Linux con acceso a `/run/journal`.
- **El puerto 9598 no responde:** revisar que Vector arrancó y que el sink Prometheus está habilitado.
- **El contenedor no inicia:** revisar la salida de `entrypoint.sh`; valida variables y el archivo generado antes de arrancar Vector.

## Seguridad

- Nunca incluir `SENTINEL_API_KEY` en una imagen, commit o log.
- Usar TLS cuando el backend no esté en localhost.
- Mantener el socket Docker en modo `ro` cuando sea posible.
- Ejecutar el agente como usuario no-root.
- Revocar una API key comprometida desde `Connections`.
- No exponer `:9598` públicamente sin autenticación o una red de monitoreo segura.

## Referencias

- [Guía principal](../README.md)
- [Arquitectura técnica del agente](../docs/architecture/agent-architecture.md)
- [Configuración Vector](configs/vector.toml)
- [Dockerfile](Dockerfile)
- [Compose auxiliar](deploy/docker-compose.yml)

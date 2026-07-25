# SentinelMonitorIA Agent Architecture

## 🏗️ Visión General

El SentinelMonitorIA Agent es un agente de telemetría de alto rendimiento basado en Vector que recolecta métricas, logs y datos de rendimiento de servidores y contenedores Docker. Está diseñado para ser ligero, seguro y tolerante a fallos.

## 🎯 Objetivos de Diseño

1. **Bajo Consumo de Recursos**: < 100MB RAM, < 5% CPU en idle
2. **Alto Rendimiento**: Hasta 10,000 eventos/segundo por agente
3. **Tolerancia a Fallos**: Buffer local de 1GB, reintentos automáticos
4. **Seguridad**: Autenticación por token, TLS end-to-end
5. **Observabilidad**: Métricas internas via Prometheus

## 🏗️ Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Server / Container                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  System  │  │   App    │  │  Docker  │  │  Custom  │   │
│  │  Metrics │  │   Logs   │  │  Metrics │  │  Sources │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│         │             │             │             │         │
└─────────┼─────────────┼─────────────┼─────────────┼─────────┘
          │             │             │             │
          ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                 Vector Processing Pipeline                   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Source  │  │ Transform │  │  Buffer  │  │   Sink   │   │
│  │  Layer   │──▶│  Layer   │──▶│  Layer  │──▶│  Layer  │───▶
│  │ (Inputs) │  │  (VRL)   │  │ (Disk)   │  │ (Output) │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────┐
│                SentinelMonitorIA Cloud API                   │
│                  POST /api/v1/telemetry                      │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Componentes Principales

### 1. **Sources (Entradas)**

#### System Metrics
- **Host Metrics Collector**: CPU, RAM, Disks, Network, Processes
- **Frecuencia**: 10 segundos por defecto
- **Tecnología**: Vector built-in `host_metrics` source

#### System Logs
- **Journald**: Logs del sistema via systemd
- **Archivos de Log**: `/var/log/*.log`, syslog, messages
- **Parseo Multilínea**: Soporte para logs con stack traces

#### Docker Metrics
- **Docker Logs**: Logs stdout/stderr de contenedores
- **Docker API**: Métricas de contenedores e imágenes
- **Socket**: `/var/run/docker.sock` (montado como volumen)

#### Custom Sources
- **Exec Source**: Scripts personalizados
- **File Source**: Archivos personalizados
- **HTTP Source**: Endpoints HTTP/Webhooks

### 2. **Transforms (Procesamiento VRL)**

#### Parse System Logs
```toml
[transforms.parse_system_logs]
type = "remap"
source = '''
# Extraer nivel de log
if match(.message, r'ERROR|FATAL') {
  .level = "error"
} else if match(.message, r'WARN|WARNING') {
  .level = "warning"
} else {
  .level = "info"
}

# Añadir metadatos
.host = hostname!()
.timestamp = now()
'''
```

#### Enrich System Metrics
- **Categorización**: CPU, Memory, Disk, Network
- **Normalización**: Unidades consistentes
- **Metadata**: Hostname, agent version, platform

#### Parse Docker Logs
- **Container ID**: Extraer ID corto (12 caracteres)
- **Image Name**: Identificar imagen origen
- **Log Level**: Parsear niveles de Docker

### 3. **Buffer Layer**

#### Configuración
```toml
[transforms.local_buffer]
type = "buffer"
buffer.type = "disk"
buffer.max_size = 1073741824  # 1GB
buffer.when_full = "block"
buffer.max_events = 100000
```

#### Características
- **Tolerancia a Fallos**: Sobrevive a reinicios
- **Priorización**: FIFO con capacidad de LIFO para críticos
- **Compresión**: Opcional para optimizar espacio

### 4. **Sink Layer (Salidas)**

#### SentinelMonitorIA API
- **Protocolo**: HTTP/HTTPS
- **Autenticación**: Bearer Token
- **Compresión**: Gzip para optimizar ancho de banda
- **Rate Limiting**: 100 requests/segundo

#### Local Metrics (Prometheus)
- **Endpoint**: `:9598/metrics`
- **Formato**: OpenMetrics
- **Métricas**: Eventos procesados, errores, latencia

#### Local Logs (Debugging)
- **Console**: stdout/stderr
- **Archivos**: Logs rotativos
- **Journald**: Integración con systemd

## ⚡ Pipeline de Procesamiento

### Flujo de Datos
```
Raw Data → Parse → Enrich → Filter → Buffer → Send → ACK
```

### Etapas del Pipeline
1. **Ingestión**: Datos crudos desde múltiples fuentes
2. **Parseo**: Extraer estructura de datos no estructurados
3. **Enriquecimiento**: Añadir metadatos y contexto
4. **Filtrado**: Eliminar datos irrelevantes
5. **Buffer**: Almacenamiento temporal tolerante a fallos
6. **Envío**: Transmisión segura a la nube
7. **Confirmación**: ACK del servidor

## 🔒 Modelo de Seguridad

### Autenticación
```
┌─────────┐    Token JWT    ┌─────────┐
│ Agent   │───────────────▶│  API    │
└─────────┘                └─────────┘
```

- **Token Bearer**: JWT firmado por el servidor
- **Rotación Automática**: Tokens expiran cada 24h
- **Validación Local**: Verificación de firma antes de enviar

### Transporte
- **TLS 1.3**: Encriptación end-to-end
- **Certificados**: Validación de CA raíz
- **Cipher Suites**: Modernos y seguros

### Aislamiento
- **Usuario No-Root**: Ejecución con usuario dedicado
- **Capabilities Limitadas**: Solo las necesarias
- **Namespaces**: Aislamiento de procesos

## ���� Métricas Internas

### Vector Metrics
```prometheus
# Throughput
vector_events_processed_total{component="source_*"}
vector_events_discarded_total{component="*"}

# Performance
vector_component_received_events_total{component="*"}
vector_component_sent_events_total{component="*"}

# Errors
vector_component_errors_total{component="*"}
vector_component_panic_total{component="*"}
```

### System Metrics (via Vector)
```prometheus
# Resource Usage
system_cpu_seconds_total{mode="*"}
system_memory_used_bytes
system_disk_used_bytes{device="*"}

# Network
system_network_receive_bytes_total{interface="*"}
system_network_transmit_bytes_total{interface="*"}
```

### Custom Metrics
```prometheus
# Agent Health
sentinel_agent_up 1
sentinel_agent_version{version="1.0.0"}
sentinel_agent_build_info{commit="abc123", build_date="*"}

# Connectivity
sentinel_api_requests_total{status="success|error"}
sentinel_api_latency_seconds{quantile="0.5|0.95|0.99"}
```

## 🐳 Deployment Options

### Docker
```yaml
version: '3.8'
services:
  sentinel-agent:
    image: sentinelmonitoria/agent:latest
    environment:
      - SENTINEL_API_KEY=${API_KEY}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /var/log:/var/log:ro
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: sentinel-agent
spec:
  template:
    spec:
      containers:
      - name: agent
        image: sentinelmonitoria/agent:latest
        env:
        - name: SENTINEL_API_KEY
          valueFrom:
            secretKeyRef:
              name: sentinel-secrets
              key: api-key
```

### Bare Metal
```bash
# Install script
curl -fsSL https://get.sentinelmonitoria.com/install.sh | sudo bash

# Configure
sudo sentinel-agent configure --api-key YOUR_KEY
```

## 🔧 Configuración Avanzada

### Variables de Entorno
```bash
# Required
SENTINEL_API_KEY="your-api-key"

# Optional
SENTINEL_API_ENDPOINT="https://api.sentinelmonitoria.com"
SENTINEL_AGENT_VERSION="1.0.0"
SENTINEL_HOSTNAME="$(hostname)"
SENTINEL_AGENT_ID="$(uuidgen)"
VECTOR_LOG_LEVEL="info"
```

### Configuración de Buffer
```toml
# Memory buffer (fast)
buffer.type = "memory"
buffer.max_events = 10000

# Disk buffer (persistent)
buffer.type = "disk"
buffer.max_size = 1073741824  # 1GB
```

### Rate Limiting
```toml
[sink.sentinel_api]
rate_limit_duration_secs = 1
rate_limit_num = 100
```

## 🐛 Troubleshooting

### Comandos de Diagnóstico
```bash
# Check agent status
systemctl status sentinel-agent

# View logs
journalctl -u sentinel-agent -f

# Test connectivity
curl -H "Authorization: Bearer $API_KEY" \
  https://api.sentinelmonitoria.com/api/v1/health

# Check metrics
curl http://localhost:9598/metrics

# Validate config
vector validate /etc/sentinelmonitoria/vector.toml
```

### Errores Comunes

#### 1. Permisos de Docker
```bash
# Solution
sudo chmod 666 /var/run/docker.sock
# Or better
sudo usermod -aG docker sentinel
```

#### 2. Rate Limiting
```toml
# Config adjustment
rate_limit_num = 200
rate_limit_duration_secs = 2
```

#### 3. Buffer Lleno
```toml
# Increase buffer size
buffer.max_size = 2147483648  # 2GB
buffer.when_full = "drop_newest"
```

## 🔮 Roadmap

### Próximas Versiones
1. **v1.1**: Soporte para Windows
2. **v1.2**: Integración con Kubernetes Operator
3. **v1.3**: Plugin system para fuentes personalizadas
4. **v2.0**: Edge computing con procesamiento local de IA

### Características Planeadas
- **Streaming en tiempo real**: WebSockets para baja latencia
- **Compresión adaptativa**: LZ4, Zstd según ancho de banda
- **Policy-based filtering**: Reglas dinámicas de filtrado
- **Multi-tenancy**: Soporte para múltiples organizaciones por agente

## 📚 Referencias

- [Vector Documentation](https://vector.dev/docs/)
- [VRL Language Guide](https://vector.dev/docs/reference/vrl/)
- [Prometheus Metrics](https://prometheus.io/docs/concepts/metric_types/)
- [Docker Metrics API](https://docs.docker.com/engine/api/v1.43/)

## 🤝 Contribución

Consulta el [README principal](../../README.md) para el flujo de desarrollo; las pautas específicas de contribución del agente aún no están definidas.
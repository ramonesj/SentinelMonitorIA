# SentinelMonitorIA Agent Docker Image
# Multi-stage build para tamaño optimizado

# Stage 1: Builder
FROM rust:1.75-alpine AS builder

# Instalar dependencias de compilación
RUN apk add --no-cache \
    git \
    curl \
    build-base \
    openssl-dev \
    pkgconfig \
    cmake \
    perl

# Descargar y compilar Vector desde fuente
WORKDIR /build
ARG VECTOR_VERSION=0.36.0

RUN curl -L -o vector.tar.gz "https://github.com/vectordotdev/vector/archive/refs/tags/v${VECTOR_VERSION}.tar.gz" && \
    tar -xzf vector.tar.gz && \
    mv "vector-${VECTOR_VERSION}" vector && \
    cd vector && \
    cargo build --release --no-default-features --features "sources-host_metrics,sources-journald,sources-file,sources-docker_logs,transforms,sinks-http,sinks-console,sinks-prometheus"

# Stage 2: Runtime
FROM alpine:3.19

# Instalar dependencias de runtime
RUN apk add --no-cache \
    ca-certificates \
    tzdata \
    libgcc \
    libssl3 \
    musl \
    docker-cli \
    docker-cli-compose \
    jq \
    curl \
    bash \
    sudo

# Crear usuario y grupos no-root
RUN addgroup -S docker && \
    addgroup -S sentinel && \
    adduser -S sentinel -G sentinel && \
    adduser sentinel docker

# Crear estructura de directorios
RUN mkdir -p /etc/sentinelmonitoria \
             /var/lib/sentinelmonitoria \
             /var/log/sentinelmonitoria \
             /opt/sentinelmonitoria/bin

# Copiar binario de Vector
COPY --from=builder /build/vector/target/release/vector /usr/local/bin/vector

# Copiar archivos de configuración
COPY configs/vector.toml /etc/sentinelmonitoria/vector.toml
COPY deploy/healthcheck.sh /opt/sentinelmonitoria/bin/healthcheck.sh
COPY deploy/entrypoint.sh /opt/sentinelmonitoria/bin/entrypoint.sh

# Scripts de utilidad
RUN echo '#!/bin/sh\nvector --version' > /opt/sentinelmonitoria/bin/version.sh && \
    echo '#!/bin/sh\nvector validate /etc/sentinelmonitoria/vector.toml' > /opt/sentinelmonitoria/bin/validate.sh

# Configurar permisos
RUN chmod +x /usr/local/bin/vector \
             /opt/sentinelmonitoria/bin/*.sh && \
    chown -R sentinel:sentinel /etc/sentinelmonitoria \
                               /var/lib/sentinelmonitoria \
                               /var/log/sentinelmonitoria \
                               /opt/sentinelmonitoria

# Variables de entorno por defecto
ENV SENTINEL_API_ENDPOINT="https://api.sentinelmonitoria.com"
ENV SENTINEL_AGENT_VERSION="1.0.0"
ENV SENTINEL_HOSTNAME=""
ENV SENTINEL_AGENT_ID=""
ENV VECTOR_LOG_LEVEL="info"
ENV RUST_LOG="info"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /opt/sentinelmonitoria/bin/healthcheck.sh

# Exponer puerto para métricas Prometheus
EXPOSE 9598

# Directorio de trabajo
WORKDIR /var/lib/sentinelmonitoria

# Cambiar a usuario no-root
USER sentinel

# Entrypoint
ENTRYPOINT ["/opt/sentinelmonitoria/bin/entrypoint.sh"]

# Comando por defecto
# El entrypoint inyecta --config; no repetir argumentos por defecto.
CMD []
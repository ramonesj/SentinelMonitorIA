#!/bin/sh
set -euo pipefail

# SentinelMonitorIA Agent Health Check
# Verifica que el agente esté funcionando correctamente

# URL para verificar métricas internas (si está expuesta)
METRICS_URL="http://localhost:9598/metrics"
HEALTH_TIMEOUT=5

# Verificar si Vector está ejecutándose
if ! pgrep -x "vector" > /dev/null; then
    echo "Vector process not running"
    exit 1
fi

# Opcional: Verificar métricas Prometheus si están expuestas
if curl --max-time ${HEALTH_TIMEOUT} --silent --fail "${METRICS_URL}" > /dev/null 2>&1; then
    # Verificar que hay métricas siendo recolectadas
    if curl --max-time ${HEALTH_TIMEOUT} --silent "${METRICS_URL}" | grep -q "vector_events_processed_total"; then
        echo "Vector is healthy and processing events"
        exit 0
    else
        echo "Vector is running but not processing events"
        exit 1
    fi
else
    # Si no podemos conectar a métricas, solo verificamos que el proceso esté vivo
    if kill -0 $(pgrep -x "vector") 2>/dev/null; then
        echo "Vector process is alive"
        exit 0
    else
        echo "Vector process is not responding"
        exit 1
    fi
fi
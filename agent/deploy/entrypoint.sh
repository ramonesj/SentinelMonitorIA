#!/bin/bash
set -euo pipefail

# SentinelMonitorIA Agent Entrypoint
# Configuración dinámica y validación de entorno

# Cargar variables de entorno desde archivo si existe
if [ -f "/etc/sentinelmonitoria/.env" ]; then
    echo "📁 Cargando variables de entorno desde /etc/sentinelmonitoria/.env"
    export $(grep -v '^#' /etc/sentinelmonitoria/.env | xargs)
fi

# Validar variables de entorno requeridas
echo "🔍 Validando configuración..."

if [ -z "${SENTINEL_API_KEY:-}" ]; then
    echo "❌ ERROR: SENTINEL_API_KEY no está configurada"
    echo ""
    echo "Configuración requerida:"
    echo "  1. Configure SENTINEL_API_KEY con su API Key"
    echo "  2. Opcionalmente, configure SENTINEL_API_ENDPOINT si usa un endpoint personalizado"
    echo ""
    echo "Ejemplo:"
    echo "  docker run -e SENTINEL_API_KEY=tu_api_key sentinelmonitoria/agent"
    echo "  docker run -e SENTINEL_API_KEY=tu_api_key -e SENTINEL_API_ENDPOINT=https://api.tudominio.com sentinelmonitoria/agent"
    exit 1
fi

# Configurar hostname si no está definido
if [ -z "${SENTINEL_HOSTNAME:-}" ]; then
    export SENTINEL_HOSTNAME=$(hostname)
    echo "📝 Usando hostname del sistema: ${SENTINEL_HOSTNAME}"
fi

# Generar Agent ID si no existe
if [ -z "${SENTINEL_AGENT_ID:-}" ]; then
    if command -v uuidgen >/dev/null 2>&1; then
        export SENTINEL_AGENT_ID=$(uuidgen)
    else
        # Fallback a un ID basado en hostname y timestamp
        export SENTINEL_AGENT_ID="agent-$(hostname)-$(date +%s)"
    fi
    echo "🆔 Agent ID generado: ${SENTINEL_AGENT_ID}"
fi

# Crear archivo de configuración dinámico
echo "⚙️  Generando configuración dinámica..."

# Plantilla para variables de entorno en vector.toml
CONFIG_TEMPLATE="/etc/sentinelmonitoria/vector.toml"
CONFIG_OUTPUT="/tmp/vector-generated.toml"

# Reemplazar variables de entorno en la plantilla
envsubst < "$CONFIG_TEMPLATE" > "$CONFIG_OUTPUT"

# Validar configuración de Vector
echo "🔧 Validando configuración de Vector..."
if vector validate "$CONFIG_OUTPUT" > /dev/null 2>&1; then
    echo "✅ Configuración de Vector válida"
else
    echo "❌ Error en la configuración de Vector"
    vector validate "$CONFIG_OUTPUT"
    exit 1
fi

# Mostrar resumen de configuración
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "           SENTINELMONITORIA AGENT CONFIGURATION               "
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "🔗 API Endpoint: ${SENTINEL_API_ENDPOINT:-https://api.sentinelmonitoria.com}"
echo "🔑 API Key: ${SENTINEL_API_KEY:0:8}******"
echo "🖥️  Hostname: ${SENTINEL_HOSTNAME}"
echo "🆔 Agent ID: ${SENTINEL_AGENT_ID}"
echo "📊 Log Level: ${VECTOR_LOG_LEVEL:-info}"
echo "📁 Config File: ${CONFIG_OUTPUT}"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Verificar conectividad con Docker si está configurado
if grep -q "docker" "$CONFIG_OUTPUT"; then
    echo "🐳 Verificando conectividad con Docker..."
    if docker ps > /dev/null 2>&1; then
        echo "✅ Docker disponible"
    else
        echo "⚠️  Docker no disponible - las métricas de Docker no funcionarán"
        echo "   Asegúrese de montar /var/run/docker.sock:/var/run/docker.sock"
    fi
fi

# Ejecutar Vector con la configuración generada
echo "🚀 Iniciando SentinelMonitorIA Agent..."
exec vector --config "$CONFIG_OUTPUT" "$@"
#!/bin/bash

# SentinelMonitorIA Agent Installer
# Version: 1.0.0
# Author: SentinelMonitorIA Team

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables configurables
SENTINEL_VERSION="1.0.0"
VECTOR_VERSION="0.36.0"
INSTALL_DIR="/opt/sentinelmonitoria"
CONFIG_DIR="/etc/sentinelmonitoria"
LOG_DIR="/var/log/sentinelmonitoria"
DATA_DIR="/var/lib/sentinelmonitoria"
SERVICE_USER="sentinel"
SERVICE_GROUP="sentinel"

# URLs de descarga
VECTOR_URL="https://packages.timber.io/vector/${VECTOR_VERSION}/vector-${VECTOR_VERSION}-x86_64-unknown-linux-gnu.tar.gz"
SENTINEL_AGENT_URL="https://github.com/sentinelmonitoria/agent/releases/download/v${SENTINEL_VERSION}/sentinel-agent-v${SENTINEL_VERSION}-linux-amd64.tar.gz"

# Funciones de logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar si se está ejecutando como root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Este script debe ejecutarse como root (sudo)"
        exit 1
    fi
}

# Detectar distribución Linux
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    case $ID in
        ubuntu|debian)
            DISTRO="debian"
            ;;
        centos|rhel|fedora|amazon)
            DISTRO="rhel"
            ;;
        *)
            DISTRO="unknown"
            ;;
    esac
    
    log_info "Detectado: $OS $VER ($DISTRO)"
}

# Instalar dependencias del sistema
install_dependencies() {
    log_info "Instalando dependencias del sistema..."
    
    case $DISTRO in
        debian)
            apt-get update
            apt-get install -y curl wget gnupg lsb-release ca-certificates \
                systemd docker.io jq gzip tar
            ;;
        rhel)
            yum install -y curl wget epel-release jq gzip tar \
                systemd docker
            ;;
        *)
            log_warning "Distribución no soportada. Se requieren: curl, wget, tar, gzip, systemd"
            ;;
    esac
}

# Crear usuario y grupos del sistema
create_system_user() {
    log_info "Creando usuario y grupo del sistema..."
    
    if ! getent group $SERVICE_GROUP > /dev/null; then
        groupadd --system $SERVICE_GROUP
        log_success "Grupo $SERVICE_GROUP creado"
    fi
    
    if ! id -u $SERVICE_USER > /dev/null 2>&1; then
        useradd --system --no-create-home \
                --shell /usr/sbin/nologin \
                --gid $SERVICE_GROUP \
                $SERVICE_USER
        log_success "Usuario $SERVICE_USER creado"
    fi
}

# Instalar Vector
install_vector() {
    log_info "Instalando Vector ${VECTOR_VERSION}..."
    
    # Crear directorio temporal
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Descargar Vector
    log_info "Descargando Vector..."
    curl -L -o vector.tar.gz "$VECTOR_URL"
    
    # Extraer y mover archivos
    tar -xzf vector.tar.gz
    cp vector-${VECTOR_VERSION}/bin/vector /usr/local/bin/
    chmod +x /usr/local/bin/vector
    
    # Verificar instalación
    if vector --version &>/dev/null; then
        log_success "Vector instalado correctamente"
    else
        log_error "Error al instalar Vector"
        exit 1
    fi
    
    # Limpiar
    cd /
    rm -rf "$TEMP_DIR"
}

# Crear estructura de directorios
create_directories() {
    log_info "Creando estructura de directorios..."
    
    mkdir -p "$INSTALL_DIR"/{bin,configs,logs}
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    
    # Configurar permisos
    chown -R $SERVICE_USER:$SERVICE_GROUP "$INSTALL_DIR"
    chown -R $SERVICE_USER:$SERVICE_GROUP "$CONFIG_DIR"
    chown -R $SERVICE_USER:$SERVICE_GROUP "$LOG_DIR"
    chown -R $SERVICE_USER:$SERVICE_GROUP "$DATA_DIR"
    
    chmod 750 "$INSTALL_DIR"
    chmod 755 "$CONFIG_DIR"
    chmod 755 "$LOG_DIR"
    chmod 755 "$DATA_DIR"
    
    log_success "Directorios creados con permisos adecuados"
}

# Copiar archivos de configuración
copy_config_files() {
    log_info "Copiando archivos de configuración..."
    
    # Archivo de configuración principal
    cp "$(dirname "$0")/../configs/vector.toml" "$CONFIG_DIR/vector.toml"
    
    # Archivo de variables de entorno
    cat > "$CONFIG_DIR/.env" << EOF
# SentinelMonitorIA Agent Environment Variables
SENTINEL_API_ENDPOINT=https://api.sentinelmonitoria.com
SENTINEL_API_KEY=YOUR_API_KEY_HERE
SENTINEL_AGENT_VERSION=${SENTINEL_VERSION}
SENTINEL_HOSTNAME=$(hostname)
SENTINEL_AGENT_ID=$(uuidgen)
EOF
    
    # Script de configuración
    cat > "$INSTALL_DIR/bin/configure.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

CONFIG_DIR="/etc/sentinelmonitoria"
ENV_FILE="$CONFIG_DIR/.env"

echo "🔄 Configurando SentinelMonitorIA Agent"
echo ""

read -p "Ingrese el endpoint de la API [https://api.sentinelmonitoria.com]: " API_ENDPOINT
API_ENDPOINT=${API_ENDPOINT:-https://api.sentinelmonitoria.com}

read -p "Ingrese su API Key: " API_KEY
if [ -z "$API_KEY" ]; then
    echo "❌ API Key es requerida"
    exit 1
fi

# Actualizar archivo .env
sed -i "s|SENTINEL_API_ENDPOINT=.*|SENTINEL_API_ENDPOINT=${API_ENDPOINT}|" "$ENV_FILE"
sed -i "s|SENTINEL_API_KEY=.*|SENTINEL_API_KEY=${API_KEY}|" "$ENV_FILE"

# Generar nuevo ID de agente si no existe
if ! grep -q "SENTINEL_AGENT_ID=" "$ENV_FILE" || grep -q "SENTINEL_AGENT_ID=YOUR_" "$ENV_FILE"; then
    NEW_ID=$(uuidgen)
    sed -i "s|SENTINEL_AGENT_ID=.*|SENTINEL_AGENT_ID=${NEW_ID}|" "$ENV_FILE"
fi

# Actualizar hostname
CURRENT_HOSTNAME=$(hostname)
sed -i "s|SENTINEL_HOSTNAME=.*|SENTINEL_HOSTNAME=${CURRENT_HOSTNAME}|" "$ENV_FILE"

echo "✅ Configuración actualizada"
echo ""
echo "Resumen:"
echo "  Endpoint: ${API_ENDPOINT}"
echo "  Hostname: ${CURRENT_HOSTNAME}"
echo "  Agent ID: $(grep SENTINEL_AGENT_ID "$ENV_FILE" | cut -d'=' -f2)"
echo ""
echo "Reinicie el servicio para aplicar cambios:"
echo "  sudo systemctl restart sentinel-agent"
EOF
    
    chmod +x "$INSTALL_DIR/bin/configure.sh"
    chown $SERVICE_USER:$SERVICE_GROUP "$INSTALL_DIR/bin/configure.sh"
    
    log_success "Archivos de configuración copiados"
}

# Crear servicio systemd
create_systemd_service() {
    log_info "Creando servicio systemd..."
    
    cat > /etc/systemd/system/sentinel-agent.service << EOF
[Unit]
Description=SentinelMonitorIA Agent - Telemetry Collection Service
Documentation=https://docs.sentinelmonitoria.com
After=network.target docker.service
Wants=network.target
Requires=docker.socket

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_GROUP
EnvironmentFile=$CONFIG_DIR/.env
ExecStart=/usr/local/bin/vector --config $CONFIG_DIR/vector.toml
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sentinel-agent
LimitNOFILE=65536
LimitNPROC=65536
LimitCORE=infinity
TimeoutStopSec=30

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
ReadWritePaths=$DATA_DIR $LOG_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    # Recargar systemd
    systemctl daemon-reload
    log_success "Servicio systemd creado"
}

# Configurar logrotate
setup_logrotate() {
    log_info "Configurando logrotate..."
    
    cat > /etc/logrotate.d/sentinel-agent << EOF
$LOG_DIR/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 640 $SERVICE_USER $SERVICE_GROUP
    sharedscripts
    postrotate
        systemctl reload sentinel-agent > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log_success "Logrotate configurado"
}

# Configurar firewall (opcional)
setup_firewall() {
    log_info "Configurando reglas de firewall..."
    
    # Solo si firewalld está instalado
    if command -v firewall-cmd &>/dev/null; then
        firewall-cmd --permanent --add-port=9598/tcp  # Métricas Prometheus
        firewall-cmd --reload
        log_success "Reglas de firewall añadidas"
    else
        log_warning "firewalld no encontrado, omitiendo configuración de firewall"
    fi
}

# Probar la instalación
test_installation() {
    log_info "Probando instalación..."
    
    # Verificar que Vector está instalado
    if ! vector --version &>/dev/null; then
        log_error "Vector no está instalado correctamente"
        return 1
    fi
    
    # Verificar archivos de configuración
    if [ ! -f "$CONFIG_DIR/vector.toml" ]; then
        log_error "Archivo de configuración no encontrado"
        return 1
    fi
    
    # Verificar servicio systemd
    if ! systemctl is-enabled sentinel-agent &>/dev/null; then
        log_error "Servicio no habilitado"
        return 1
    fi
    
    log_success "Instalación verificada correctamente"
    return 0
}

# Mostrar resumen de instalación
show_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "               INSTALACIÓN COMPLETADA                         "
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "🎉 SentinelMonitorIA Agent ha sido instalado correctamente!"
    echo ""
    echo "📁 Directorios creados:"
    echo "   Configuración: $CONFIG_DIR"
    echo "   Logs: $LOG_DIR"
    echo "   Datos: $DATA_DIR"
    echo "   Binarios: $INSTALL_DIR/bin"
    echo ""
    echo "⚙️  Servicio:"
    echo "   Habilitado: systemctl enable sentinel-agent"
    echo "   Iniciado: systemctl start sentinel-agent"
    echo "   Estado: systemctl status sentinel-agent"
    echo ""
    echo "🔧 Configuración:"
    echo "   Editar configuración: sudo nano $CONFIG_DIR/.env"
    echo "   Configurar agente: sudo $INSTALL_DIR/bin/configure.sh"
    echo ""
    echo "📊 Métricas:"
    echo "   Métricas Prometheus: http://localhost:9598/metrics"
    echo ""
    echo "📝 Logs:"
    echo "   Ver logs: sudo journalctl -u sentinel-agent -f"
    echo ""
    echo "⚠️  IMPORTANTE:"
    echo "   1. Actualice su API Key en $CONFIG_DIR/.env"
    echo "   2. Configure el endpoint si es necesario"
    echo "   3. Reinicie el servicio después de configurar"
    echo ""
    echo "❓ Ayuda:"
    echo "   Documentación: https://docs.sentinelmonitoria.com"
    echo "   Soporte: support@sentinelmonitoria.com"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

# Función principal
main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║       SentinelMonitorIA Agent Installer v${SENTINEL_VERSION}       ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    
    # Verificar root
    check_root
    
    # Detectar distribución
    detect_distro
    
    # Instalar dependencias
    install_dependencies
    
    # Crear usuario del sistema
    create_system_user
    
    # Instalar Vector
    install_vector
    
    # Crear directorios
    create_directories
    
    # Copiar archivos de configuración
    copy_config_files
    
    # Crear servicio systemd
    create_systemd_service
    
    # Configurar logrotate
    setup_logrotate
    
    # Configurar firewall
    setup_firewall
    
    # Habilitar e iniciar servicio
    log_info "Habilitando e iniciando servicio..."
    systemctl enable sentinel-agent
    systemctl start sentinel-agent
    
    # Probar instalación
    if test_installation; then
        show_summary
    else
        log_error "Hubo problemas con la instalación"
        exit 1
    fi
}

# Manejar señales
trap 'log_error "Instalación interrumpida"; exit 1' INT TERM

# Ejecutar función principal
main "$@"
#!/bin/bash

# SentinelMonitorIA Agent Build Script
# Builds and packages the agent for distribution

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AGENT_DIR="$PROJECT_ROOT/agent"
BUILD_DIR="$PROJECT_ROOT/build"
VERSION=$(grep -oP 'SENTINEL_VERSION="\K[^"]+' "$AGENT_DIR/deploy/install.sh" || echo "1.0.0")
ARCH="x86_64"
PLATFORM="linux"

# Functions
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

# Clean build directory
clean_build() {
    log_info "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
}

# Build Docker image
build_docker_image() {
    log_info "Building Docker image..."
    
    cd "$AGENT_DIR"
    
    # Build image
    docker build \
        -t sentinelmonitoria/agent:"$VERSION" \
        -t sentinelmonitoria/agent:latest \
        .
    
    # Save image to tar
    docker save sentinelmonitoria/agent:"$VERSION" \
        -o "$BUILD_DIR/sentinel-agent-$VERSION-docker.tar"
    
    log_success "Docker image built and saved"
}

# Create tarball package
create_tarball_package() {
    log_info "Creating tarball package..."
    
    PACKAGE_DIR="$BUILD_DIR/sentinel-agent-$VERSION-$PLATFORM-$ARCH"
    mkdir -p "$PACKAGE_DIR"
    
    # Copy installation files
    cp -r "$AGENT_DIR/configs" "$PACKAGE_DIR/"
    cp -r "$AGENT_DIR/deploy" "$PACKAGE_DIR/"
    cp "$PROJECT_ROOT/LICENSE" "$PACKAGE_DIR/"
    cp "$AGENT_DIR/README.md" "$PACKAGE_DIR/"
    
    # Create version file
    echo "version: $VERSION" > "$PACKAGE_DIR/VERSION"
    echo "platform: $PLATFORM-$ARCH" >> "$PACKAGE_DIR/VERSION"
    echo "build_date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$PACKAGE_DIR/VERSION"
    
    # Create install script wrapper
    cat > "$PACKAGE_DIR/install.sh" << EOF
#!/bin/bash
# SentinelMonitorIA Agent Installer Wrapper
set -euo pipefail

# Check if running as root
if [ "\$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Run actual installer
cd "\$(dirname "\$0")"
exec ./deploy/install.sh
EOF
    
    chmod +x "$PACKAGE_DIR/install.sh"
    
    # Create tarball
    cd "$BUILD_DIR"
    tar -czf "sentinel-agent-$VERSION-$PLATFORM-$ARCH.tar.gz" \
        "sentinel-agent-$VERSION-$PLATFORM-$ARCH"
    
    log_success "Tarball package created"
}

# Create DEB package (for Debian/Ubuntu)
create_deb_package() {
    log_info "Creating DEB package..."
    
    DEB_DIR="$BUILD_DIR/deb"
    mkdir -p "$DEB_DIR/DEBIAN"
    mkdir -p "$DEB_DIR/usr/local/bin"
    mkdir -p "$DEB_DIR/etc/sentinelmonitoria"
    mkdir -p "$DEB_DIR/var/lib/sentinelmonitoria"
    mkdir -p "$DEB_DIR/var/log/sentinelmonitoria"
    
    # Control file
    cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: sentinel-agent
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: docker.io, curl, wget, jq, systemd
Maintainer: SentinelMonitorIA Team <support@sentinelmonitoria.com>
Description: SentinelMonitorIA Agent - Telemetry Collection Service
 Agent for collecting system metrics, logs, and Docker telemetry.
EOF
    
    # Pre-install script
    cat > "$DEB_DIR/DEBIAN/preinst" << 'EOF'
#!/bin/bash
# Pre-installation script
set -e

echo "Preparing for SentinelMonitorIA Agent installation..."
EOF
    
    # Post-install script
    cat > "$DEB_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
# Post-installation script
set -e

echo "Configuring SentinelMonitorIA Agent..."

# Create system user if it doesn't exist
if ! getent group sentinel > /dev/null; then
    groupadd --system sentinel
fi

if ! id -u sentinel > /dev/null 2>&1; then
    useradd --system --no-create-home \
            --shell /usr/sbin/nologin \
            --gid sentinel \
            sentinel
fi

# Set permissions
chown -R sentinel:sentinel /etc/sentinelmonitoria \
                           /var/lib/sentinelmonitoria \
                           /var/log/sentinelmonitoria

echo "Agent installed successfully. Please configure with:"
echo "  sudo sentinel-agent configure"
EOF
    
    # Pre-remove script
    cat > "$DEB_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
# Pre-removal script
set -e

echo "Stopping SentinelMonitorIA Agent..."
systemctl stop sentinel-agent || true
systemctl disable sentinel-agent || true
EOF
    
    # Post-remove script
    cat > "$DEB_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
# Post-removal script
set -e

echo "Cleaning up SentinelMonitorIA Agent..."

# Remove configuration if purging
if [ "$1" = "purge" ]; then
    rm -rf /etc/sentinelmonitoria
    rm -rf /var/lib/sentinelmonitoria
    rm -rf /var/log/sentinelmonitoria
fi

echo "Agent removal complete."
EOF
    
    # Set permissions
    chmod 755 "$DEB_DIR/DEBIAN"/*
    
    # Copy files
    cp "$AGENT_DIR/configs/vector.toml" "$DEB_DIR/etc/sentinelmonitoria/"
    
    # Build package
    dpkg-deb --build "$DEB_DIR" \
        "$BUILD_DIR/sentinel-agent_${VERSION}_amd64.deb"
    
    log_success "DEB package created"
}

# Create RPM package (for RHEL/CentOS/Fedora)
create_rpm_package() {
    log_info "Creating RPM package..."
    
    RPM_DIR="$BUILD_DIR/rpm"
    SPEC_DIR="$RPM_DIR/SPECS"
    SOURCE_DIR="$RPM_DIR/SOURCES"
    BUILDROOT_DIR="$RPM_DIR/BUILDROOT"
    
    mkdir -p "$SPEC_DIR" "$SOURCE_DIR" "$BUILDROOT_DIR"
    
    # Spec file
    cat > "$SPEC_DIR/sentinel-agent.spec" << EOF
Name: sentinel-agent
Version: $VERSION
Release: 1%{?dist}
Summary: SentinelMonitorIA Agent - Telemetry Collection Service
License: Apache 2.0
URL: https://sentinelmonitoria.com
Source0: sentinel-agent-%{version}.tar.gz

BuildArch: x86_64
Requires: docker, curl, wget, jq, systemd

%description
Agent for collecting system metrics, logs, and Docker telemetry
for the SentinelMonitorIA observability platform.

%prep
%setup -q

%build
# Nothing to build - it's a configuration package

%install
mkdir -p %{buildroot}/etc/sentinelmonitoria
mkdir -p %{buildroot}/var/lib/sentinelmonitoria
mkdir -p %{buildroot}/var/log/sentinelmonitoria

install -m 644 configs/vector.toml %{buildroot}/etc/sentinelmonitoria/

%pre
getent group sentinel >/dev/null || groupadd -r sentinel
getent passwd sentinel >/dev/null || \
    useradd -r -g sentinel -s /sbin/nologin -c "SentinelMonitorIA Agent" sentinel

%post
systemctl daemon-reload

%preun
if [ \$1 -eq 0 ]; then
    systemctl stop sentinel-agent || true
    systemctl disable sentinel-agent || true
fi

%postun
systemctl daemon-reload || true

%files
%attr(640, sentinel, sentinel) /etc/sentinelmonitoria/vector.toml
%dir %attr(750, sentinel, sentinel) /etc/sentinelmonitoria
%dir %attr(750, sentinel, sentinel) /var/lib/sentinelmonitoria
%dir %attr(750, sentinel, sentinel) /var/log/sentinelmonitoria

%changelog
* $(date +"%a %b %d %Y") SentinelMonitorIA Team <support@sentinelmonitoria.com> - $VERSION-1
- Initial package
EOF
    
    # Create source tarball
    cd "$AGENT_DIR"
    tar -czf "$SOURCE_DIR/sentinel-agent-$VERSION.tar.gz" \
        --transform "s,^,sentinel-agent-$VERSION/," \
        configs/
    
    # Build RPM
    rpmbuild --define "_topdir $RPM_DIR" \
             --define "_buildrootdir $BUILDROOT_DIR" \
             -bb "$SPEC_DIR/sentinel-agent.spec"
    
    # Copy built RPM
    cp "$RPM_DIR/RPMS/x86_64/sentinel-agent-$VERSION-1.*.rpm" \
        "$BUILD_DIR/sentinel-agent-$VERSION.x86_64.rpm"
    
    log_success "RPM package created"
}

# Generate checksums
generate_checksums() {
    log_info "Generating checksums..."
    
    cd "$BUILD_DIR"
    
    # SHA256 checksums
    for file in sentinel-agent-*; do
        if [ -f "$file" ]; then
            sha256sum "$file" > "$file.sha256"
        fi
    done
    
    # MD5 checksums
    for file in sentinel-agent-*; do
        if [ -f "$file" ] && [[ ! "$file" =~ \.sha256$ ]]; then
            md5sum "$file" > "$file.md5"
        fi
    done
    
    # Create checksum manifest
    cat > "$BUILD_DIR/CHECKSUMS.txt" << EOF
SentinelMonitorIA Agent $VERSION Checksums
Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Platform: $PLATFORM-$ARCH

Files:
EOF
    
    for file in sentinel-agent-*; do
        if [ -f "$file" ] && [[ ! "$file" =~ \.(sha256|md5)$ ]]; then
            echo "" >> "$BUILD_DIR/CHECKSUMS.txt"
            echo "File: $file" >> "$BUILD_DIR/CHECKSUMS.txt"
            echo "Size: $(stat -c%s "$file") bytes" >> "$BUILD_DIR/CHECKSUMS.txt"
            
            if [ -f "$file.sha256" ]; then
                echo "SHA256: $(cat "$file.sha256" | cut -d' ' -f1)" >> "$BUILD_DIR/CHECKSUMS.txt"
            fi
            
            if [ -f "$file.md5" ]; then
                echo "MD5: $(cat "$file.md5" | cut -d' ' -f1)" >> "$BUILD_DIR/CHECKSUMS.txt"
            fi
        fi
    done
    
    log_success "Checksums generated"
}

# Show build summary
show_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "               BUILD COMPLETED                                "
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "📦 Build directory: $BUILD_DIR"
    echo ""
    echo "📁 Generated artifacts:"
    echo ""
    
    cd "$BUILD_DIR"
    for file in sentinel-agent-*; do
        if [ -f "$file" ] && [[ ! "$file" =~ \.(sha256|md5)$ ]]; then
            size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
            human_size=$(numfmt --to=iec --suffix=B "$size" 2>/dev/null || echo "${size}B")
            echo "  • $file ($human_size)"
        fi
    done
    
    echo ""
    echo "🔐 Checksums:"
    echo "  • CHECKSUMS.txt"
    echo "  • *.sha256 files"
    echo "  • *.md5 files"
    echo ""
    echo "🐳 Docker image:"
    echo "  • sentinelmonitoria/agent:$VERSION"
    echo "  • sentinelmonitoria/agent:latest"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Test the packages"
    echo "  2. Upload to package repository"
    echo "  3. Update documentation"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

# Main function
main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║       SentinelMonitorIA Agent Build v$VERSION             ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    
    # Clean
    clean_build
    
    # Build Docker image
    build_docker_image
    
    # Create packages
    create_tarball_package
    create_deb_package
    create_rpm_package
    
    # Generate checksums
    generate_checksums
    
    # Show summary
    show_summary
}

# Run main function
main "$@"
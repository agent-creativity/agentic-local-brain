#!/bin/bash
#
# LocalBrain Installer for macOS/Linux
#
# Usage:
#   curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
#
# Environment variables:
#   LOCALBRAIN_SERVER  - Server URL (default: http://localbrain.oss-cn-shanghai.aliyuncs.com)
#   LOCALBRAIN_VERSION - Version to install (default: latest)

set -e

# Configuration
SERVER_URL="${LOCALBRAIN_SERVER:-http://localbrain.oss-cn-shanghai.aliyuncs.com}"
VERSION="${LOCALBRAIN_VERSION:-latest}"
INSTALL_DIR="$HOME/.localbrain"
BIN_DIR="$INSTALL_DIR/bin"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Detect OS and architecture
detect_platform() {
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    
    case "$ARCH" in
        x86_64|amd64) ARCH="x64" ;;
        arm64|aarch64) ARCH="arm64" ;;
    esac
    
    PLATFORM="${OS}-${ARCH}"
    info "Detected platform: $PLATFORM"
}

# Detect shell and config file
detect_shell() {
    SHELL_NAME=$(basename "$SHELL")
    
    case "$SHELL_NAME" in
        zsh) SHELL_RC="$HOME/.zshrc" ;;
        bash) SHELL_RC="$HOME/.bashrc" ;;
        fish) SHELL_RC="$HOME/.config/fish/config.fish" ;;
        *) SHELL_RC="$HOME/.profile" ;;
    esac
    
    info "Detected shell: $SHELL_NAME ($SHELL_RC)"
}

# Check if already installed
check_existing() {
    if [ -f "$BIN_DIR/localbrain" ]; then
        warn "LocalBrain is already installed at $BIN_DIR/localbrain"
        info "Run 'localbrain self-update' to update to the latest version"
        exit 0
    fi
}

# Download file with retry
download() {
    local url="$1"
    local output="$2"
    local max_retries=3
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        if curl -fsSL --connect-timeout 30 "$url" -o "$output"; then
            return 0
        fi
        retry=$((retry + 1))
        warn "Download failed, retrying ($retry/$max_retries)..."
        sleep $((2 ** retry))
    done
    
    error "Failed to download after $max_retries attempts"
}

# Fetch version info
fetch_version_info() {
    local url="$SERVER_URL/version.json"
    info "Fetching version info from $url"
    
    VERSION_JSON=$(curl -fsSL "$url")
    
    if [ -z "$VERSION_JSON" ]; then
        error "Failed to fetch version info"
    fi
    
    if [ "$VERSION" = "latest" ]; then
        # Extract version - prefer jq if available, fallback to grep
        if command -v jq &> /dev/null; then
            VERSION=$(echo "$VERSION_JSON" | jq -r '.version')
        else
            VERSION=$(echo "$VERSION_JSON" | grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | cut -d'"' -f4)
        fi
        info "Latest version: $VERSION"
    fi
}

# Download binary
download_binary() {
    local filename="localbrain-${PLATFORM}"
    local url="${SERVER_URL}/binary_installer/releases/v${VERSION}/${filename}"
    local temp_file=$(mktemp)
    
    info "Downloading binary from $url"
    download "$url" "$temp_file"
    
    # Create bin directory
    mkdir -p "$BIN_DIR"
    
    # Move binary
    mv "$temp_file" "$BIN_DIR/localbrain"
    chmod +x "$BIN_DIR/localbrain"
    
    info "Binary installed to $BIN_DIR/localbrain"
}

# Add to PATH
add_to_path() {
    local path_entry="export PATH=\"$HOME/.localbrain/bin:\$PATH\""
    
    # Check if already in PATH
    if echo "$PATH" | grep -q ".localbrain/bin"; then
        info "Already in PATH"
        return
    fi
    
    # Check if entry exists in shell config
    if [ -f "$SHELL_RC" ] && grep -q ".localbrain/bin" "$SHELL_RC"; then
        info "PATH entry already in $SHELL_RC"
        return
    fi
    
    # Add to shell config
    echo "" >> "$SHELL_RC"
    echo "# LocalBrain" >> "$SHELL_RC"
    echo "$path_entry" >> "$SHELL_RC"
    
    info "Added to PATH in $SHELL_RC"
    info "Run 'source $SHELL_RC' or start a new shell to use localbrain"
}

# Write install info
write_install_info() {
    local install_info="$INSTALL_DIR/.install-info"
    local install_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local source_url="${SERVER_URL}/releases/v${VERSION}/localbrain-${PLATFORM}"
    
    cat > "$install_info" << EOF
{
  "version": "$VERSION",
  "install_time": "$install_time",
  "install_path": "$BIN_DIR/localbrain",
  "source_url": "$source_url",
  "platform": "$OS",
  "architecture": "$ARCH"
}
EOF
    
    info "Install info written to $install_info"
}

# Run first-time check
run_check() {
    if [ -x "$BIN_DIR/localbrain" ]; then
        info "Running installation check..."
        "$BIN_DIR/localbrain" doctor || true
    fi
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}✓ LocalBrain installed successfully!${NC}"
    echo ""
    echo "Version: $VERSION"
    echo "Binary:  $BIN_DIR/localbrain"
    echo ""
    echo "Next steps:"
    echo "  1. Run 'source $SHELL_RC' or start a new terminal"
    echo "  2. Run 'localbrain init setup' to initialize"
    echo "  3. Run 'localbrain doctor' to verify installation"
    echo ""
}

# Main
main() {
    info "Installing LocalBrain..."
    
    detect_platform
    detect_shell
    check_existing
    fetch_version_info
    download_binary
    write_install_info
    add_to_path
    run_check
    print_success
}

main "$@"

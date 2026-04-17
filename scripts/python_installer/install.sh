#!/bin/bash
#
# LocalBrain Python Installer for macOS/Linux
#
# Usage:
#   curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
#
# Environment variables:
#   LOCALBRAIN_SERVER  - Server URL (default: http://localbrain.oss-cn-shanghai.aliyuncs.com)
#   LOCALBRAIN_VERSION - Version to install (default: latest)

set -e

# Configuration
SERVER_URL="${LOCALBRAIN_SERVER:-http://localbrain.oss-cn-shanghai.aliyuncs.com}"
VERSION="${LOCALBRAIN_VERSION:-latest}"
INSTALL_DIR="$HOME/.localbrain"
VENV_DIR="$INSTALL_DIR/venv"
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

# Check Python
check_python() {
    if ! command -v python3 > /dev/null 2>&1; then
        error "Python 3.8+ is required. Please install Python first."
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    REQUIRED_VERSION="3.8"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        error "Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION"
    fi
    
    info "Python $PYTHON_VERSION detected"
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
    if [ -d "$VENV_DIR" ]; then
        warn "Virtual environment already exists at $VENV_DIR"
        info "Removing existing venv for clean install"
        rm -rf "$VENV_DIR"
    fi
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
        if command -v jq > /dev/null 2>&1; then
            VERSION=$(echo "$VERSION_JSON" | jq -r '.version')
        else
            VERSION=$(echo "$VERSION_JSON" | grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | cut -d'"' -f4)
        fi
        info "Latest version: $VERSION"
    fi
}

# Create virtual environment
create_venv() {
    info "Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    info "Virtual environment created"
}

# Download and install wheel
install_wheel() {
    WHEEL_URL="$SERVER_URL/python_installer/packages/localbrain-$VERSION-py3-none-any.whl"
    
    info "Downloading wheel from $WHEEL_URL"
    
    # Activate venv and install
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip --quiet
    pip install "$WHEEL_URL"
    deactivate
    
    info "Wheel installed successfully"
}

# Create symlink
create_symlink() {
    mkdir -p "$BIN_DIR"
    
    ln -sf "$VENV_DIR/bin/localbrain" "$BIN_DIR/localbrain"
    chmod +x "$BIN_DIR/localbrain"
    
    info "Created symlink: $BIN_DIR/localbrain"
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
}

# Write install info
write_install_info() {
    local install_info="$INSTALL_DIR/.install-info"
    local install_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    cat > "$install_info" << EOF
{
  "version": "$VERSION",
  "install_time": "$install_time",
  "install_path": "$BIN_DIR/localbrain",
  "install_type": "python",
  "source_url": "$SERVER_URL/python_installer/packages/localbrain-$VERSION-py3-none-any.whl",
  "venv_path": "$VENV_DIR"
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
    echo "Type:    Python (venv)"
    echo "Binary:  $BIN_DIR/localbrain"
    echo "Venv:    $VENV_DIR"
    echo ""
    echo "Next steps:"
    echo "  1. Run 'source $SHELL_RC' or start a new terminal"
    echo "  2. Run 'localbrain init setup' to initialize"
    echo "  3. Run 'localbrain doctor' to verify installation"
    echo ""
}

# Main
main() {
    info "Installing LocalBrain (Python method)..."
    
    check_python
    detect_shell
    check_existing
    fetch_version_info
    create_venv
    install_wheel
    create_symlink
    write_install_info
    add_to_path
    run_check
    print_success
}

main "$@"

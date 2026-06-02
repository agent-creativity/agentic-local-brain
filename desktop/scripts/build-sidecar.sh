#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$DESKTOP_DIR")"
BINARIES_DIR="$DESKTOP_DIR/src-tauri/binaries"

# Detect platform
ARCH=$(uname -m)
case "$ARCH" in
    x86_64|amd64) TARGET_TRIPLE="x86_64-apple-darwin" ;;
    arm64|aarch64) TARGET_TRIPLE="aarch64-apple-darwin" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

echo "Building localbrain sidecar for $TARGET_TRIPLE..."

# Build with PyInstaller from project root
cd "$PROJECT_ROOT"

# Ensure virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Build single-file executable
pyinstaller \
    --onefile \
    --name "localbrain" \
    --distpath "$BINARIES_DIR" \
    --noconfirm \
    --console \
    --add-data "kb:kb" \
    --add-data "VERSION:." \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import fastapi \
    --hidden-import chromadb \
    --hidden-import schedule \
    --hidden-import croniter \
    --collect-data litellm \
    kb/cli.py

# Rename to include target triple (required by Tauri sidecar)
mv "$BINARIES_DIR/localbrain" "$BINARIES_DIR/localbrain-$TARGET_TRIPLE"
chmod +x "$BINARIES_DIR/localbrain-$TARGET_TRIPLE"

echo "Sidecar built: $BINARIES_DIR/localbrain-$TARGET_TRIPLE"
echo "Size: $(du -sh "$BINARIES_DIR/localbrain-$TARGET_TRIPLE" | cut -f1)"

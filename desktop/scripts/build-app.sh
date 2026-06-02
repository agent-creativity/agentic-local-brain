#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== LocalBrain macOS App Build ==="

# Step 1: Build sidecar
echo ""
echo "Step 1/3: Building sidecar binary..."
bash "$SCRIPT_DIR/build-sidecar.sh"

# Step 2: Build frontend
echo ""
echo "Step 2/3: Building frontend..."
cd "$DESKTOP_DIR"
npm run build

# Step 3: Build Tauri app
echo ""
echo "Step 3/3: Building Tauri app..."
export PATH="$HOME/.cargo/bin:$PATH"
npm run tauri build

echo ""
echo "=== Build Complete ==="
echo "App:  $DESKTOP_DIR/src-tauri/target/release/bundle/macos/LocalBrain.app"
echo "DMG:  $DESKTOP_DIR/src-tauri/target/release/bundle/dmg/"

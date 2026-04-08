#!/usr/bin/env bash
#
# local-build-release.sh
#
# Local-only release pipeline:
#   1. Build release artifacts (wheel + binary)
#   2. Copy to the publish repository static directory
#   3. Commit and push the publish repository
#
# Usage:
#   ./scripts/local-build-release.sh              # uses version from VERSION file
#   ./scripts/local-build-release.sh 0.5.3        # override version
#

set -euo pipefail

# ── Paths ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PUBLISH_STATIC="/Users/xudonglai/AliDrive/Work/local-brain/static"

# ── Version ─────────────────────────────────────────────────────────
if [ -n "${1:-}" ]; then
    VERSION="$1"
else
    VERSION="$(cat "$PROJECT_DIR/VERSION" | tr -d '[:space:]')"
fi

echo "============================================================"
echo " Local Build & Release  v${VERSION}"
echo "============================================================"
echo ""

# ── Step 1: Build release ──────────────────────────────────────────
echo "[1/3] Building release artifacts..."
echo ""
python3 "$PROJECT_DIR/scripts/build_release.py" --version "$VERSION"
echo ""

# ── Step 2: Copy to publish repo ───────────────────────────────────
echo "[2/3] Copying artifacts to publish repository..."

if [ ! -d "$PUBLISH_STATIC" ]; then
    echo "  ERROR: Publish directory not found: $PUBLISH_STATIC"
    exit 1
fi

DIST_DIR="$PROJECT_DIR/dist"

# Copy python installer
cp -R "$DIST_DIR/python_installer/" "$PUBLISH_STATIC/python_installer/"
echo "  Copied: python_installer/"

# Copy binary installer
cp -R "$DIST_DIR/binary_installer/" "$PUBLISH_STATIC/binary_installer/"
echo "  Copied: binary_installer/"

# Copy version.json
cp "$DIST_DIR/version.json" "$PUBLISH_STATIC/version.json"
echo "  Copied: version.json"

# Copy skill assets (SKILL.md + package.json)
SKILL_SRC="$PROJECT_DIR/kb/web/static/docs/skills/knowledge-collect-localbrain"
SKILL_DST="$PUBLISH_STATIC/skills/knowledge-collect-localbrain"
mkdir -p "$SKILL_DST"
cp -R "$SKILL_SRC/" "$SKILL_DST/"
echo "  Copied: skills/knowledge-collect-localbrain/"

echo ""

# ── Step 3: Commit and push publish repo ───────────────────────────
echo "[3/3] Committing and pushing publish repository..."

PUBLISH_REPO="$(cd "$PUBLISH_STATIC/.." && pwd)"

cd "$PUBLISH_REPO"
git add static/
git commit -m "release: localbrain v${VERSION}" || {
    echo "  Nothing to commit (no changes detected)"
    echo ""
    echo "============================================================"
    echo " Done — no new changes to publish"
    echo "============================================================"
    exit 0
}
git push

echo ""
echo "============================================================"
echo " Release v${VERSION} published successfully!"
echo "============================================================"
echo ""
echo " Artifacts deployed to: $PUBLISH_STATIC"
echo " Version JSON:          $PUBLISH_STATIC/version.json"
echo ""

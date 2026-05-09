#!/usr/bin/env bash
# Package the Flashcard Guru Remote add-on into a .ankiaddon zip ready
# for upload to AnkiWeb (or sideload via "Open With → Anki" / drag-and-drop).
#
# Output: dist/flashcard-guru-remote-<version>.ankiaddon
#
# Important: AnkiWeb expects __init__.py and manifest.json at the root of
# the zip, not nested inside a package directory. We keep the dev-time
# `flashcard_guru_remote/` package layout for clean imports/tests, and
# flatten it here at build time.
#
# Usage: ./scripts/build_ankiaddon.sh

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 required" >&2
  exit 1
fi

VERSION=$(python3 -c "import json; print(json.load(open('manifest.json'))['human_version'])")
DIST="dist"
STAGE="$DIST/_stage"
OUT="$DIST/flashcard-guru-remote-${VERSION}.ankiaddon"

echo "==> Cleaning previous build"
rm -rf "$STAGE" "$OUT"
mkdir -p "$STAGE"

echo "==> Vendoring runtime deps (websockets + qrcode)"
./scripts/vendor_deps.sh >/dev/null

echo "==> Staging files (flattened — package files at zip root)"
cp manifest.json "$STAGE/"
# Copy package contents *into* the staging root so __init__.py lives
# alongside manifest.json.
cp -R flashcard_guru_remote/. "$STAGE/"

# Strip dev-only artifacts that snuck in via the vendor pull or local
# pytest runs.
find "$STAGE" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$STAGE" -type d -name "*.dist-info" -prune -exec rm -rf {} +
find "$STAGE" -name "*.pyc" -delete
find "$STAGE" -name ".DS_Store" -delete

echo "==> Sanity check"
test -f "$STAGE/manifest.json"   || { echo "missing manifest.json" >&2; exit 1; }
test -f "$STAGE/__init__.py"     || { echo "missing __init__.py at root" >&2; exit 1; }
test -f "$STAGE/server.py"       || { echo "missing server.py" >&2; exit 1; }
test -f "$STAGE/dispatcher.py"   || { echo "missing dispatcher.py" >&2; exit 1; }
test -d "$STAGE/vendor"          || { echo "missing vendor/ — run scripts/vendor_deps.sh" >&2; exit 1; }
test -d "$STAGE/vendor/websockets" || { echo "missing vendor/websockets" >&2; exit 1; }
test -d "$STAGE/vendor/qrcode"     || { echo "missing vendor/qrcode" >&2; exit 1; }

echo "==> Zipping"
( cd "$STAGE" && zip -qr "../$(basename "$OUT")" . )
rm -rf "$STAGE"

echo ""
echo "Built: $OUT"
ls -la "$OUT"
echo ""
echo "Sideload test:"
echo "  open -a Anki '$OUT'"
echo ""
echo "AnkiWeb upload:"
echo "  https://ankiweb.net/shared/upload"

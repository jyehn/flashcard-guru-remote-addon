#!/usr/bin/env bash
# Populate flashcard_guru_remote/vendor/ with runtime deps.
#
# AnkiWeb add-ons cannot pip-install, so we ship copies of:
#   - websockets (pure Python, ~250KB)
#   - qrcode (pure Python, ~50KB; PIL is provided by Anki itself)
#
# Usage: ./scripts/vendor_deps.sh

set -euo pipefail

cd "$(dirname "$0")/.."

VENDOR_DIR="flashcard_guru_remote/vendor"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "==> Cleaning vendor dir"
rm -rf "$VENDOR_DIR"
mkdir -p "$VENDOR_DIR"

echo "==> Downloading websockets + qrcode into $TMP_DIR"
python3 -m pip install \
  --target "$TMP_DIR" \
  --no-deps \
  --upgrade \
  "websockets>=12.0" \
  "qrcode>=7.4"

echo "==> Copying packages into $VENDOR_DIR"
for pkg in websockets qrcode; do
  if [ -d "$TMP_DIR/$pkg" ]; then
    cp -R "$TMP_DIR/$pkg" "$VENDOR_DIR/$pkg"
  else
    echo "ERROR: $pkg not found after pip install" >&2
    exit 1
  fi
done

echo "==> Removing dist-info / cache"
find "$VENDOR_DIR" -type d -name "__pycache__" -exec rm -rf {} +
find "$VENDOR_DIR" -type d -name "*.dist-info" -exec rm -rf {} +
find "$VENDOR_DIR" -type d -name "*.egg-info" -exec rm -rf {} +

touch "$VENDOR_DIR/__init__.py"

echo "==> Done. Vendor contents:"
ls -1 "$VENDOR_DIR"

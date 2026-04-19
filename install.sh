#!/usr/bin/env bash
# Compatibility wrapper for legacy install command usage.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -x "$SCRIPT_DIR/setup.sh" ]; then
    echo "Error: setup.sh not found or not executable in $SCRIPT_DIR" >&2
    exit 1
fi

echo "[i] install.sh is deprecated. Redirecting to setup.sh install..."
exec "$SCRIPT_DIR/setup.sh" install "$@"

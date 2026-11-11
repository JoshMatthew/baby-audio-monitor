#!/bin/bash
# Stops the transmitter and removes it from the baby Mac.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/paths.sh"

launchctl bootout "$SERVICE" 2>/dev/null || true
rm -f "$PLIST"
rm -rf "$APP_DIR"

echo "Transmitter removed. The log is still at $LOG_FILE"

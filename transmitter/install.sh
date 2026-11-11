#!/bin/bash
# Installs the transmitter on the baby Mac as a background service that starts at login
# and restarts itself if it ever stops.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/paths.sh"

if ! command -v uv >/dev/null && [ ! -x "$HOME/.local/bin/uv" ]; then
  echo "Installing uv, which runs the transmitter..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"

read -rp "Server URL (like https://baby-monitor.fly.dev): " SERVER_URL
read -rsp "Transmitter token: " TOKEN
echo

mkdir -p "$APP_DIR" "$(dirname "$PLIST")" "$(dirname "$LOG_FILE")"
cp "$SCRIPT_DIR/transmitter.py" "$APP_DIR/transmitter.py"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$UV</string>
    <string>run</string>
    <string>--quiet</string>
    <string>--script</string>
    <string>$APP_DIR/transmitter.py</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>BABY_MONITOR_SERVER</key>
    <string>$SERVER_URL</string>
    <key>BABY_MONITOR_TOKEN</key>
    <string>$TOKEN</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>30</integer>
  <key>ProcessType</key>
  <string>Interactive</string>
  <key>StandardOutPath</key>
  <string>$LOG_FILE</string>
  <key>StandardErrorPath</key>
  <string>$LOG_FILE</string>
</dict>
</plist>
EOF
chmod 600 "$PLIST"
plutil -lint "$PLIST" >/dev/null

launchctl bootout "$SERVICE" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Transmitter installed and running."
echo "Watch it with: tail -f \"$LOG_FILE\""

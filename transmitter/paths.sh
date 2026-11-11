# Where the transmitter lives on the baby Mac. Shared by install.sh and uninstall.sh.
LABEL="com.babymonitor.transmitter"
SERVICE="gui/$(id -u)/$LABEL"
APP_DIR="$HOME/Library/Application Support/BabyMonitor"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_FILE="$HOME/Library/Logs/baby-monitor.log"

#!/bin/zsh

# OMEGA Persistence Layer
# Ensures the OMEGA Core (hexstrike_server.py) is registered and persistent.

CORE_DIR="/Users/thealchemist/hexstrike-ai/hexstrike-ai"
PLIST_PATH="$HOME/Library/LaunchAgents/com.omega.core.plist"
PYTHON_PATH=$(which python3)

echo "🛡️ [OMEGA-PERSISTENCE] Initializing Terminal Protection..."

# 1. Create the LaunchAgent PLIST
cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.omega.core</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$CORE_DIR/hexstrike_server.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$CORE_DIR/omega_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$CORE_DIR/omega_stderr.log</string>
    <key>WorkingDirectory</key>
    <string>$CORE_DIR</string>
</dict>
</plist>
EOF

# 2. Set permissions
chmod 644 "$PLIST_PATH"

# 3. Load the agent
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"

echo "✅ [OMEGA-PERSISTENCE] Core registered. Persistence Active on Reboot."
echo "👁️ [OMEGA-PERSISTENCE] Log monitoring via: tail -f $CORE_DIR/omega_stdout.log"

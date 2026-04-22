#!/bin/bash
# TodoScope.app launcher — runs server in Terminal, stays alive in Dock.
#
# Double-click .app → Terminal opens with server output → browser opens.
# Close the Terminal tab to stop the server.
# Cmd+Q the .app to remove the Dock icon.

DIR="$(dirname "$0")"
BINARY="$DIR/../Resources/todoscope"

# Launch the binary in a new Terminal window
osascript <<EOF
tell application "Terminal"
    activate
    do script "'$BINARY'"
end tell
EOF

# Stay alive so .app icon remains in the Dock.
# The sleep loop keeps this process running until Cmd+Q.
while true; do
    sleep 86400
done

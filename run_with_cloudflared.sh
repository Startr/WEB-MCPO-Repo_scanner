#!/bin/bash
# Script to run the Flask TODO Scanner with hot reloading and expose it via Cloudflare Tunnel
# Usage: ./run_with_cloudflared.sh

# Set environment variables for Flask
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

echo "Starting Flask in development mode with hot reloading..."
echo "Code changes will automatically reload the server"

# Start Flask app in the background with hot reloading enabled
python -m flask run --host=0.0.0.0 --port=5000 --debug &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 2
echo "Flask server running with PID: $FLASK_PID"

# Store PID in a file for later reference
echo $FLASK_PID > .flask.pid

# Start cloudflared in a separate terminal with trap to handle interrupts
echo "Starting cloudflared tunnel to expose http://localhost:5000 ..."
echo "Your app will be available via a public URL"
echo "Press Ctrl+C to stop the server and tunnel"

# Handle interrupts properly
cleanup() {
    echo "Shutting down..."
    # Kill Flask process if it's still running
    if [ -f .flask.pid ]; then
        pid=$(cat .flask.pid)
        if ps -p $pid > /dev/null; then
            echo "Stopping Flask server (PID: $pid)"
            kill $pid
        fi
        rm .flask.pid
    fi
    exit 0
}

# Set up cleanup on script exit
trap cleanup INT TERM EXIT

# Start cloudflared - this will run in foreground
cloudflared tunnel --url http://localhost:5000

#!/bin/bash
# Script to run the Flask TODO Scanner and expose it via Cloudflare Tunnel
# Usage: ./run_with_cloudflared.sh

# Start Flask app in the background
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000 &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 2

echo "Starting cloudflared tunnel to expose http://localhost:5000 ..."
cloudflared tunnel --url http://localhost:5000

# When cloudflared exits, stop Flask
kill $FLASK_PID

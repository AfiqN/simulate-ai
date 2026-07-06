#!/bin/bash
# Start local SearXNG instance for SimulateAI RAG
# Usage: bash scripts/start-searxng.sh

SEARXNG_DIR="/tmp/searxng"
SETTINGS_DIR="/tmp/searxng-data"
PORT=8888

# Check if already running
if curl -s "http://127.0.0.1:$PORT" > /dev/null 2>&1; then
    echo "✓ SearXNG already running on port $PORT"
    exit 0
fi

# Clone if not present
if [ ! -d "$SEARXNG_DIR" ]; then
    echo "Cloning SearXNG..."
    git clone https://github.com/searxng/searxng.git "$SEARXNG_DIR"
fi

# Create settings
mkdir -p "$SETTINGS_DIR"
cat > "$SETTINGS_DIR/settings.yml" << 'EOF'
use_default_settings: true

general:
  debug: false
  instance_name: "SimulateAI Search"

server:
  port: 8888
  bind_address: "127.0.0.1"
  secret_key: "simulateai-local-dev-key"
  limiter: false

search:
  safe_search: 0
  default_lang: "auto"
  formats:
    - html
    - json

outgoing:
  request_timeout: 8.0
EOF

# Start
cd "$SEARXNG_DIR"
SEARXNG_SETTINGS_PATH="$SETTINGS_DIR/settings.yml" \
    nohup python3 -m searx.webapp > /tmp/searxng.log 2>&1 &

echo "Starting SearXNG on port $PORT..."
sleep 3

# Verify
if curl -s "http://127.0.0.1:$PORT" > /dev/null 2>&1; then
    echo "✓ SearXNG running on http://127.0.0.1:$PORT"
else
    echo "✗ Failed to start. Check /tmp/searxng.log"
    tail -10 /tmp/searxng.log
    exit 1
fi

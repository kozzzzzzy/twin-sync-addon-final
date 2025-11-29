#!/bin/bash
set -e

echo "=========================================="
echo "TwinSync Spot - Starting..."
echo "=========================================="

# Read Gemini API key from addon options
if [ -f /data/options.json ]; then
    GEMINI_API_KEY=$(cat /data/options.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('gemini_api_key', ''))")
    export GEMINI_API_KEY
    echo "Gemini API key: configured"
else
    echo "Warning: /data/options.json not found"
fi

# Export supervisor token if available
if [ -n "$SUPERVISOR_TOKEN" ]; then
    export SUPERVISOR_TOKEN
    echo "Supervisor token: available"
fi

# Set data directory
export DATA_DIR="/data"

# Get ingress path from supervisor if available
if [ -n "$SUPERVISOR_TOKEN" ]; then
    INGRESS_INFO=$(curl -s -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" http://supervisor/addons/self/info 2>/dev/null || echo "{}")
    INGRESS_ENTRY=$(echo "$INGRESS_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('ingress_entry', ''))" 2>/dev/null || echo "")
    if [ -n "$INGRESS_ENTRY" ]; then
        export INGRESS_PATH="$INGRESS_ENTRY"
        echo "Ingress path: $INGRESS_PATH"
    fi
fi

echo "Starting FastAPI server on port 8099..."
echo "=========================================="

# Run the FastAPI app
cd /app
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099

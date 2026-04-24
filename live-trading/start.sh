#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV="${1:-dev}"
ENV_FILE=".env.${ENV}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found"
    echo "Usage: ./start.sh [dev|prod]"
    exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)

HOST_PORT="${HOST_PORT:-8080}"

echo "Starting L-Shape Trading Engine (${ENV})..."
podman-compose up -d

echo ""
echo "Container started. Access at http://localhost:${HOST_PORT}"
echo ""
echo "View logs: podman-compose logs -f"
echo "Stop: ./stop.sh"

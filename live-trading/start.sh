#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

HOST_PORT="${HOST_PORT:-8080}"

echo "Building and starting L-Shape Trading Engine..."
podman-compose up -d --build

echo ""
echo "Container started. Access at http://localhost:${HOST_PORT}"
echo ""
echo "View logs: podman-compose logs -f"
echo "Stop: ./stop.sh"

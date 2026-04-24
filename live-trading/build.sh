#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV="${1:-dev}"
ENV_FILE=".env.${ENV}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found"
    echo "Usage: ./build.sh [dev|prod]"
    exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "Building L-Shape Trading Engine (${ENV})..."
podman-compose build

echo ""
echo "Build complete."
echo "Run ./start.sh ${ENV} to start the container."

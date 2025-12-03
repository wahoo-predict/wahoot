#!/bin/bash

# Script to start local Subtensor chain with persistent volume
# This keeps your wallets and subnet setup across restarts

set -e

echo "Checking for existing local_chain container..."

# Determine docker command (try without sudo first, then with sudo)
DOCKER_CMD="docker"
if ! docker ps -a >/dev/null 2>&1; then
    if sudo docker ps -a >/dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
        echo "Using sudo for docker commands"
    else
        echo "Error: Cannot access Docker."
        echo ""
        echo "To fix permissions, run:"
        echo "  ./fix_docker_permissions.sh"
        echo ""
        echo "Or use sudo manually:"
        echo "  sudo docker ps -a"
        exit 1
    fi
fi

# Check if container exists
if $DOCKER_CMD ps -a | grep -q "local_chain"; then
    if $DOCKER_CMD ps | grep -q "local_chain"; then
        echo "✓ Container 'local_chain' is already running"
        $DOCKER_CMD ps | grep local_chain
    else
        echo "Container exists but is stopped. Starting it..."
        $DOCKER_CMD start local_chain
        echo "✓ Container started"
        echo ""
        echo "View logs with: $DOCKER_CMD logs -f local_chain"
    fi
else
    echo "Container doesn't exist. Creating with persistent volume..."
    echo ""
    echo "⚠️  IMPORTANT: This will create a persistent setup."
    echo "   Use '$DOCKER_CMD stop local_chain' and '$DOCKER_CMD start local_chain' to manage it."
    echo "   DO NOT use '$DOCKER_CMD rm' or you'll lose your setup!"
    echo ""
    
    $DOCKER_CMD run -d \
      --name local_chain \
      --restart unless-stopped \
      -p 9944:9944 -p 9945:9945 \
      -v subtensor_data:/data \
      ghcr.io/opentensor/subtensor-localnet:devnet-ready \
      False \
      --base-path /data
    
    echo "✓ Container created and started"
    echo ""
    echo "View logs with: $DOCKER_CMD logs -f local_chain"
    echo ""
    echo "For more info, see: https://docs.learnbittensor.org/local-build/create-subnet"
fi

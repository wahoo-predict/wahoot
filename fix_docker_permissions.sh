#!/bin/bash

# Script to fix Docker permissions
# This adds your user to the docker group so you don't need sudo

set -e

echo "=========================================="
echo "Docker Permissions Fix"
echo "=========================================="
echo ""

# Check if user is already in docker group
if groups | grep -q docker; then
    echo "✓ User is already in docker group"
    echo ""
    echo "If you still get permission errors, try:"
    echo "  1. Log out and log back in"
    echo "  2. Or run: newgrp docker"
    exit 0
fi

echo "Adding user to docker group..."
echo "This requires sudo privileges."
echo ""

# Add user to docker group
sudo usermod -aG docker $USER

echo ""
echo "✓ User added to docker group"
echo ""
echo "⚠️  IMPORTANT: You need to log out and log back in for changes to take effect."
echo ""
echo "Or run this command to apply changes in current session:"
echo "  newgrp docker"
echo ""
echo "After that, you should be able to run docker commands without sudo."


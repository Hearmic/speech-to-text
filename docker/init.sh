#!/bin/sh
set -e

# Create necessary directories with proper permissions
mkdir -p /tmp/whisper-cache
chmod 777 /tmp/whisper-cache

# Set environment variable for Whisper cache
export WHISPER_CACHE_DIR=/tmp/whisper-cache

# Execute the command passed to the container
exec "$@"

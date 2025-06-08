#!/bin/sh
set -e

# Create necessary directories with proper permissions
mkdir -p /home/django/.cache/whisper
chown -R django:django /home/django/.cache 2>/dev/null || true
chmod 777 /home/django/.cache/whisper 2>/dev/null || true

# Create whisper cache directory in /tmp
mkdir -p /tmp/whisper-cache
chown -R django:django /tmp/whisper-cache 2>/dev/null || true
chmod 777 /tmp/whisper-cache 2>/dev/null || true

# Create app directories if they don't exist
mkdir -p /app/staticfiles /app/media
chown -R django:django /app 2>/dev/null || true

# Set environment variable for whisper cache
# Try /tmp/whisper-cache first, fall back to /home/django/.cache/whisper
export WHISPER_CACHE_DIR=/tmp/whisper-cache
if [ ! -w "$WHISPER_CACHE_DIR" ]; then
    export WHISPER_CACHE_DIR=/home/django/.cache/whisper
    mkdir -p "$WHISPER_CACHE_DIR"
    chmod 777 "$WHISPER_CACHE_DIR" 2>/dev/null || true
fi

# Execute the command passed to the container
exec "$@"

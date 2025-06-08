#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create backups directory if it doesn't exist
mkdir -p backups

# Generate timestamp for the backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="backups/backup_${TIMESTAMP}.sql"

# Get database credentials from environment variables
DB_NAME=${DB_NAME:-speech2text}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

echo -e "${YELLOW}Creating database backup to ${BACKUP_FILE}...${NC}"

# Create the backup using pg_dump
PGPASSWORD="${DB_PASSWORD}" pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -F c -f "${BACKUP_FILE}" \
  && echo -e "${GREEN}Backup created successfully: ${BACKUP_FILE}${NC}" \
  || { echo -e "${YELLOW}Failed to create backup${NC}" >&2; exit 1; }

# Keep only the last 10 backups
BACKUP_COUNT=$(ls -1 backups/backup_*.sql 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 10 ]; then
    echo -e "${YELLOW}Removing old backups...${NC}"
    ls -t backups/backup_*.sql | tail -n +11 | xargs rm -f
    echo -e "${GREEN}Kept the 10 most recent backups.${NC}"
fi

echo -e "${GREEN}Backup process completed successfully.${NC}"

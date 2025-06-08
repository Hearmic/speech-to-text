#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide a backup file to restore.${NC}"
    echo -e "Usage: $0 <backup_file.sql>"
    echo -e "\nAvailable backups in backups/ directory:"
    ls -l backups/ 2>/dev/null || echo "No backups found in backups/ directory"
    exit 1
fi

BACKUP_FILE="$1"

# Check if the backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file '$BACKUP_FILE' not found.${NC}"
    exit 1
fi

# Get database credentials from environment variables or use defaults
DB_NAME=${DB_NAME:-speech2text}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

# Ask for confirmation
read -p "This will delete all data in the database '${DB_NAME}'. Are you sure? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Restore cancelled.${NC}"
    exit 0
fi

echo -e "${YELLOW}Restoring database from ${BACKUP_FILE}...${NC}"

# Drop and recreate the database
echo -e "${YELLOW}Recreating database...${NC}"
PGPASSWORD="${DB_PASSWORD}" dropdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" --if-exists "${DB_NAME}"
PGPASSWORD="${DB_PASSWORD}" createdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}"

# Restore the database
echo -e "${YELLOW}Restoring data...${NC}"
PGPASSWORD="${DB_PASSWORD}" pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" "${BACKUP_FILE}"

echo -e "\n${GREEN}Database restored successfully from ${BACKUP_FILE}${NC}"

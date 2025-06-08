#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables if .env exists
if [ -f .env ]; then
    echo -e "${YELLOW}Loading environment variables from .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
fi

# Set default values if not provided
DB_NAME=${DB_NAME:-speech2text}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

echo -e "${YELLOW}Setting up database...${NC}"

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}
until PGPASSWORD="${DB_PASSWORD}" pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"; do
    sleep 1
done

# Create database if it doesn't exist
if ! PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
    echo -e "${YELLOW}Creating database ${DB_NAME}...${NC}"
    PGPASSWORD="${DB_PASSWORD}" createdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}"
    echo -e "${GREEN}Database created successfully${NC}"
else
    echo -e "${GREEN}Database already exists${NC}"
fi

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}
python manage.py migrate

# Create superuser if it doesn't exist
echo -e "${YELLOW}Creating superuser...${NC}"
if ! python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists()"; then
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin')" | python manage.py shell
    echo -e "${GREEN}Superuser created successfully${NC}
Username: admin\nPassword: admin"
else
    echo -e "${YELLOW}Superuser already exists${NC}"
fi

# Initialize subscription plans
echo -e "${YELLOW}Initializing subscription plans...${NC}"
python manage.py init_subscription_plans

echo -e "\n${GREEN}Database setup completed successfully!${NC}"

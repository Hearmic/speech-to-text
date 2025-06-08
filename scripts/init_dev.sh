#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Initializing development environment...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}Created .env file. Please update it with your configuration.${NC}"
else
    echo -e "${GREEN}.env file already exists.${NC}"
fi

# Build and start the Docker containers
echo -e "${YELLOW}Building and starting Docker containers...${NC}"
docker-compose build
docker-compose up -d

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
until docker-compose exec db pg_isready -U postgres; do
    sleep 1
done

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose exec web python manage.py migrate

# Create superuser if it doesn't exist
echo -e "${YELLOW}Creating superuser...${NC}"
if ! docker-compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin')"; then
    echo -e "${YELLOW}Superuser already exists or could not be created.${NC}" >&2
fi

# Initialize subscription plans
echo -e "${YELLOW}Initializing subscription plans...${NC}"
docker-compose exec web python manage.py init_subscription_plans

echo -e "\n${GREEN}Development environment is ready!${NC}"
echo -e "\nAccess the application at: http://localhost:8000"
echo -e "Admin username: admin"
echo -e "Admin password: admin"
echo -e "\nRun 'make logs' to view the logs."

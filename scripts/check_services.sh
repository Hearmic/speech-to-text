#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a service is running
check_service() {
    local service_name=$1
    local command=$2
    
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✓${NC} ${service_name} is running"
        return 0
    else
        echo -e "${RED}✗${NC} ${service_name} is not running"
        return 1
    fi
}

echo -e "${YELLOW}Checking services...${NC}\n"

# Check Docker containers
if docker ps &>/dev/null; then
    echo -e "${GREEN}✓${NC} Docker is running"
    
    # Check if containers are running
    if [ "$(docker ps -q -f name=speech-to-text-web)" ]; then
        echo -e "  ${GREEN}✓${NC} Web container is running"
    else
        echo -e "  ${RED}✗${NC} Web container is not running"
    fi
    
    if [ "$(docker ps -q -f name=speech-to-text-db)" ]; then
        echo -e "  ${GREEN}✓${NC} Database container is running"
    else
        echo -e "  ${RED}✗${NC} Database container is not running"
    fi
    
    if [ "$(docker ps -q -f name=speech-to-text-redis)" ]; then
        echo -e "  ${GREEN}✓${NC} Redis container is running"
    else
        echo -e "  ${RED}✗${NC} Redis container is not running"
    fi
    
    if [ "$(docker ps -q -f name=speech-to-text-celery_worker)" ]; then
        echo -e "  ${GREEN}✓${NC} Celery worker container is running"
    else
        echo -e "  ${YELLOW}ℹ${NC} Celery worker container is not running (this might be expected in development)"
    fi
    
    if [ "$(docker ps -q -f name=speech-to-text-celery_beat)" ]; then
        echo -e "  ${GREEN}✓${NC} Celery beat container is running"
    else
        echo -e "  ${YELLOW}ℹ${NC} Celery beat container is not running (this might be expected in development)"
    fi
else
    echo -e "${RED}✗${NC} Docker is not running or not installed"
fi

echo

# Check if .env file exists
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
    # Source the .env file to check variables
    set -a
    source ./.env
    set +a
    
    # Check important variables
    if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your-secret-key-here" ]; then
        echo -e "  ${RED}✗${NC} SECRET_KEY is not set or is using the default value"
    else
        echo -e "  ${GREEN}✓${NC} SECRET_KEY is set"
    fi
    
    if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
        echo -e "  ${YELLOW}ℹ${NC} Database credentials are not fully configured"
    else
        echo -e "  ${GREEN}✓${NC} Database credentials are configured"
    fi
    
    if [ -z "$STRIPE_SECRET_KEY" ] || [ "$STRIPE_SECRET_KEY" = "your_stripe_secret_key" ]; then
        echo -e "  ${YELLOW}ℹ${NC} Stripe keys are not configured (required for payments)"
    else
        echo -e "  ${GREEN}✓${NC} Stripe keys are configured"
    fi
    
    if [ -z "$EMAIL_HOST_USER" ] || [ "$EMAIL_HOST_USER" = "your_sendgrid_username" ]; then
        echo -e "  ${YELLOW}ℹ${NC} Email settings are not configured"
    else
        echo -e "  ${GREEN}✓${NC} Email settings are configured"
    fi
else
    echo -e "${RED}✗${NC} .env file does not exist. Copy .env.example to .env and update the values."
fi

echo

# Check Python and Django
if command -v python &>/dev/null; then
    python_version=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
    echo -e "${GREEN}✓${NC} Python ${python_version} is installed"
    
    if python -c "import django" &>/dev/null; then
        django_version=$(python -c "import django; print(django.get_version())")
        echo -e "  ${GREEN}✓${NC} Django ${django_version} is installed"
    else
        echo -e "  ${RED}✗${NC} Django is not installed"
    fi
else
    echo -e "${RED}✗${NC} Python is not installed"
fi

echo

# Check if services are accessible
if [ "$(docker ps -q -f name=speech-to-text-db)" ]; then
    if PGPASSWORD=${DB_PASSWORD:-postgres} pg_isready -h localhost -p 5432 -U ${DB_USER:-postgres} -d ${DB_NAME:-speech2text} &>/dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL is accessible"
    else
        echo -e "${RED}✗${NC} Cannot connect to PostgreSQL"
    fi
fi

if [ "$(docker ps -q -f name=speech-to-text-redis)" ]; then
    if redis-cli -h localhost -p 6379 ping &>/dev/null; then
        echo -e "${GREEN}✓${NC} Redis is accessible"
    else
        echo -e "${RED}✗${NC} Cannot connect to Redis"
    fi
fi

echo

# Check disk space
echo -e "${YELLOW}Disk space:${NC}"
df -h | grep -v "tmpfs" | grep -v "udev" | grep -v "loop"

echo -e "\n${YELLOW}Check completed${NC}"

.PHONY: build up down logs shell test

# Build the development environment
build:
	docker-compose build

# Start the development environment
up:
	docker-compose up

# Stop the development environment
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Open a shell in the web container
shell:
	docker-compose exec web bash

# Run tests
test:
	docker-compose exec web python manage.py test

# Run migrations
migrate:
	docker-compose exec web python manage.py migrate

# Create migrations
makemigrations:
	docker-compose exec web python manage.py makemigrations

# Initialize subscription plans
init-plans:
	docker-compose exec web python manage.py init_subscription_plans

# Run production environment
prod-up:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Stop production environment
prod-down:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# View production logs
prod-logs:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Backup database
backup-db:
	docker-compose exec -T db pg_dump -U postgres speech2text > backup_$$(date +%Y%m%d_%H%M%S).sql

# Restore database
restore-db:
	cat $(file) | docker-compose exec -T db psql -U postgres speech2text

# Run management command
dj-command:
	docker-compose exec web python manage.py $(command)

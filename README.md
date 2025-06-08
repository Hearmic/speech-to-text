# Speech to Text with Whisper AI

A Django-based web application that provides speech-to-text functionality using OpenAI's Whisper AI, with a freemium subscription model.

## Features

- User authentication and authorization
- Subscription management (Free, Pro, Premium)
- Audio file upload and processing
- Speech-to-text conversion using Whisper AI
- Queue prioritization based on subscription level
- Payment processing with Stripe
- RESTful API

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Node.js and npm (for frontend development, if applicable)

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd speech-to-text
```

### 2. Set up environment variables

Copy the example environment file and update the values:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration.

### 3. Build and start the development environment

```bash
make build
make up
```

This will start the following services:
- Django web server on http://localhost:8000
- PostgreSQL database
- Redis for caching and task queue
- Celery worker for background tasks
- Celery beat for scheduled tasks

### 4. Run database migrations

```bash
make migrate
```

### 5. Initialize subscription plans

```bash
make init-plans
```

### 6. Access the application

- Web interface: http://localhost:8000
- Admin interface: http://localhost:8000/admin

## Development

### Running tests

```bash
make test
```

### Running a shell in the web container

```bash
make shell
```

### Viewing logs

```bash
make logs
```

## Production Deployment

### 1. Update environment variables

Make sure to update the `.env` file with production values, including:
- `DEBUG=False`
- A strong `SECRET_KEY`
- Production database credentials
- Email server configuration
- Stripe API keys
- AWS S3 credentials (if using S3 for media storage)

### 2. Build and start the production environment

```bash
make prod-up
```

This will build and start all services with production settings.

### 3. Run database migrations

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate
```

### 4. Collect static files

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

## Utility Scripts

The `scripts/` directory contains useful scripts for development and maintenance:

### Development Setup

- `init_dev.sh` - Initialize the complete development environment:
  - Creates .env file from .env.example if it doesn't exist
  - Builds and starts Docker containers
  - Runs database migrations
  - Creates a superuser (admin/admin)
  - Initializes subscription plans
  
  ```bash
  ./scripts/init_dev.sh
  ```

### Database Management

- `setup_db.sh` - Set up and initialize the database (useful for CI/CD and new developer setup):
  - Creates the database if it doesn't exist
  - Runs migrations
  - Creates a superuser if none exists
  - Initializes subscription plans
  
  ```bash
  # Run inside the web container or with proper database access
  ./scripts/setup_db.sh
  ```

- `backup_db.sh` - Create a backup of the database (saved to backups/ directory):
  ```bash
  # Make sure to source your .env file first or set the environment variables
  source .env
  ./scripts/backup_db.sh
  ```

- `restore_db.sh` - Restore the database from a backup:
  ```bash
  # Make sure to source your .env file first or set the environment variables
  source .env
  # List available backups
  ls -l backups/
  # Restore from a specific backup
  ./scripts/restore_db.sh backups/backup_20230101_120000.sql
  ```

### System Health Check

- `check_services.sh` - Check the status of all services and system health:
  - Docker containers status
  - Database connectivity
  - Redis connectivity
  - Environment configuration
  - Python and Django installation
  - Disk space
  
  ```bash
  ./scripts/check_services.sh
  ```

### Usage Examples

1. **First-time setup**:
   ```bash
   # Initialize the development environment
   ./scripts/init_dev.sh
   
   # Verify all services are running correctly
   ./scripts/check_services.sh
   ```

2. **Regular development workflow**:
   ```bash
   # Start services
   make up
   
   # Check service status
   ./scripts/check_services.sh
   
   # Run migrations after making model changes
   make makemigrations
   make migrate
   
   # Create a backup before major changes
   source .env
   ./scripts/backup_db.sh
   
   # Restore if needed
   ./scripts/restore_db.sh backups/backup_20230101_120000.sql
   ```

3. **Troubleshooting**:
   ```bash
   # Check service status and system health
   ./scripts/check_services.sh
   
   # Look for any errors or warnings in the output
   # Address any issues found
   
   # Check logs for more detailed information
   make logs
   ```

## Project Structure

```
.
├── app/                      # Django project root
│   ├── app/                  # Project settings and configuration
│   ├── audio/                # Audio processing app
│   ├── subscriptions/        # Subscription management app
│   ├── users/                # User management app
│   ├── manage.py             # Django management script
│   └── requirements.txt      # Python dependencies
├── docker/                   # Docker configuration files
├── .dockerignore             # Files to ignore in Docker builds
├── .env.example              # Example environment variables
├── docker-compose.yml        # Base Docker Compose configuration
├── docker-compose.override.yml # Development overrides
├── docker-compose.prod.yml   # Production overrides
├── Dockerfile               # Dockerfile for the web application
├── scripts/                  # Utility scripts
│   ├── init_dev.sh          # Initialize development environment
│   └── backup_db.sh         # Backup database
└── Makefile                 # Common commands
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Django](https://www.djangoproject.com/)
- [Whisper AI](https://openai.com/research/whisper)
- [Docker](https://www.docker.com/)
- [Celery](https://docs.celeryproject.org/)
- [Stripe](https://stripe.com/)

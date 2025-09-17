# Speech to Text with  Faster Whisper

A high-performance Django-based web application that provides speech-to-text functionality using OpenAI's Whisper AI, containerized with Docker for easy deployment and scaling.

## 🚀 Features

- **Containerized Development**: Full Docker support with optimized multi-stage builds
- **Asynchronous Processing**: Celery for background task processing
- **Scalable Architecture**: PostgreSQL database and Redis for caching and message brokering
- **Production-Ready**: Nginx as a reverse proxy with optimized configuration
- **Developer Friendly**: Comprehensive development setup with hot-reloading

## 🛠 Tech Stack

- **Backend**: Django 4.2+
- **Database**: PostgreSQL 15
- **Cache & Message Broker**: Redis 7
- **Task Queue**: Celery with Redis
- **Web Server**: Nginx
- **Containerization**: Docker + Docker Compose

## 🚀 Getting Started

### Prerequisites

- Docker 20.10.0+
- Docker Compose 2.0.0+
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd speech-to-text
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` if you need to customize any settings.

3. **Build and start the services**
   ```bash
   docker-compose --profile development up --build -d
   ```

4. **Apply database migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. **Create a superuser (optional)**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

6. **Access the application**
   - Web interface: http://localhost:8000
   - Admin interface: http://localhost:8000/admin

## 🏗 Project Structure

```
speech-to-text/
├── app/                    # Django project root
│   ├── app/               # Project settings and configuration
│   ├── main/              # Main application
│   ├── manage.py
│   └── requirements.txt
├── nginx/                 # Nginx configuration
│   └── nginx.conf
├── .env.example           # Example environment variables
├── docker-compose.yml     # Docker Compose configuration
└── Dockerfile             # Dockerfile for the web service
```

## 🔧 Development

### Running the development environment

```bash
docker-compose --profile development up --build -d
```

### Running management commands

```bash
docker-compose exec web python manage.py <command>
```

### Accessing services

- **Django Development Server**: http://localhost:8000
- **PostgreSQL**: `localhost:5432` (default credentials in .env)
- **Redis**: `localhost:6379`
- **Celery Flower** (task monitoring): http://localhost:5555

## 🚀 Production Deployment

Update `.env` with production settings:
   ```bash
   DEBUG=0
   SECRET_KEY=your-secure-secret-key
   ALLOWED_HOSTS=.yourdomain.com
   ```

### Initialize the database and create a superuser

```bash
# Run database migrations
docker-compose exec web python manage.py migrate

# Create a superuser
docker-compose exec web python manage.py createsuperuser
```

### Access the application

- **Django Admin**: http://localhost:8000/admin/
- **Main Application**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/api/docs/ (if enabled)
- **Celery Flower** (task monitoring): http://localhost:5555/

### Running management commands

To run Django management commands, use:

```bash
docker-compose exec web python manage.py <command>
```

### Running tests

```bash
# Run all tests
docker-compose exec web python manage.py test

# Run specific test module
docker-compose exec web python manage.py test app.tests
```

### Development services

The development environment includes the following services:
- **Django development server**: http://localhost:8000
- **PostgreSQL database**: `postgresql://postgres:postgres@localhost:5432/speech2text`
- **Redis**: `redis://localhost:6379`
- **Celery worker**: For background task processing
- **Celery beat**: For scheduled tasks
- **Nginx**: Reverse proxy with static file serving on http://localhost:8080

### Debugging

For debugging with VS Code, you can use the following launch configuration:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Django",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/app/manage.py",
            "args": [
                "runserver",
                "0.0.0.0:8000"
            ],
            "django": true,
            "justMyCode": true
        }
    ]
}
```
- Celery worker for background tasks
- Celery beat for scheduled tasks

### Run database migrations

```bash
make migrate
```

### Initialize subscription plans

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


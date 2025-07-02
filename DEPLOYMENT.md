# Speech to Text Application Deployment Guide

This guide provides instructions for setting up the Speech to Text application in both development and production environments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Development Setup](#development-setup)
3. [Production Deployment](#production-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Management](#database-management)
6. [Celery Workers](#celery-workers)
7. [Nginx Configuration](#nginx-configuration)
8. [SSL Certificate Setup](#ssl-certificate-setup)
9. [Maintenance](#maintenance)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Node.js and npm (for frontend development)
- Git

## Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd speech-to-text
```

### 2. Set Up Environment Variables

Copy the example environment file and update it with your configuration:

```bash
cp .env.example .env
```

Edit the `.env` file with your development settings.

### 3. Start the Development Environment

```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### 4. Run Database Migrations

```bash
docker-compose exec web python manage.py migrate
```

### 5. Create a Superuser

```bash
docker-compose exec web python manage.py createsuperuser
```

### 6. Access the Application

- **Django Admin**: http://localhost:8000/admin/
- **Main Application**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/api/docs/

## Production Deployment

### 1. Server Requirements

- Linux server (Ubuntu 20.04/22.04 recommended)
- Docker and Docker Compose
- Minimum 2 CPU cores, 4GB RAM (8GB recommended)
- Domain name with DNS configured

### 2. Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    curl \
    git \
    python3-pip \
    python3-venv \
    nginx \
    certbot \
    python3-certbot-nginx

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. Deploy the Application

```bash
# Clone the repository
git clone <repository-url> /opt/speech-to-text
cd /opt/speech-to-text

# Set up environment variables
cp .env.example .env
nano .env  # Update with production values

# Build and start the application
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Run database migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

### 4. Set Up Nginx as Reverse Proxy

Create a new Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/speech-to-text
```

Add the following configuration (replace `yourdomain.com` with your actual domain):

```nginx
upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Frame-Options "SAMEORIGIN";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    # Static files
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public, max-age=2592000";
    }
    
    # Media files
    location /media/ {
        alias /app/media/;
        expires 7d;
        access_log off;
        add_header Cache-Control "public, max-age=604800";
    }
    
    # Proxy pass to Django
    location / {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_redirect off;
        
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffer size
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
}
```

Enable the site and test the configuration:

```bash
sudo ln -s /etc/nginx/sites-available/speech-to-text /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Set Up SSL with Let's Encrypt

```bash
# Stop Nginx temporarily
sudo systemctl stop nginx

# Obtain SSL certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com --non-interactive --agree-tos --email your-email@example.com

# Start Nginx
sudo systemctl start nginx

# Set up automatic renewal
sudo crontab -e
```

Add the following line to the crontab:

```
0 0,12 * * * /usr/bin/certbot renew --quiet
```

## Environment Configuration

The application uses environment variables for configuration. Key variables include:

- `DEBUG`: Set to `False` in production
- `SECRET_KEY`: A secure secret key for Django
- `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames
- Database configuration (DB_* variables)
- Redis configuration (REDIS_* variables)
- Email settings (EMAIL_* variables)
- AWS S3 settings (if using S3 for media storage)
- Security settings (SECURE_* variables)

## Database Management

### Backing Up the Database

```bash
# Create a backup
docker-compose exec db pg_dump -U postgres speech2text > backup_$(date +%Y%m%d).sql

# Restore from backup
cat backup_file.sql | docker-compose exec -T db psql -U postgres speech2text
```

### Running Migrations

```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

## Celery Workers

### Starting Workers

```bash
# Start Celery worker
docker-compose exec -d web celery -A app worker --loglevel=info -E

# Start Celery beat for scheduled tasks
docker-compose exec -d web celery -A app beat --loglevel=info
```

### Monitoring Celery

You can monitor Celery tasks using Flower:

```bash
docker-compose exec -d web celery -A app flower --port=5555
```

Access the Flower dashboard at `http://yourdomain.com:5555`

## Nginx Configuration

The Nginx configuration includes:
- Reverse proxy to Django
- Static and media file serving
- SSL/TLS termination
- Security headers
- Gzip compression
- Caching headers

## SSL Certificate Setup

SSL certificates are managed by Let's Encrypt using Certbot. Certificates are automatically renewed before they expire.

## Maintenance

### Updating the Application

```bash
# Pull the latest changes
git pull

# Rebuild and restart the application
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Run migrations if needed
docker-compose exec web python manage.py migrate

# Collect static files if needed
docker-compose exec web python manage.py collectstatic --noinput
```

### Monitoring Logs

```bash
# View application logs
docker-compose logs -f web

# View database logs
docker-compose logs -f db

# View Celery logs
docker-compose logs -f celery_worker
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check if the database container is running: `docker-compose ps`
   - Verify database credentials in `.env`
   - Check logs: `docker-compose logs db`

2. **Static Files Not Loading**
   - Ensure `STATIC_ROOT` is set correctly
   - Run `collectstatic`: `docker-compose exec web python manage.py collectstatic --noinput`
   - Check Nginx configuration for correct static file paths

3. **Celery Worker Not Processing Tasks**
   - Check if Redis is running: `docker-compose ps`
   - Check Celery logs: `docker-compose logs celery_worker`
   - Ensure the task is properly registered and imported

4. **Nginx 502 Bad Gateway**
   - Check if the Django application is running: `docker-compose ps`
   - Check Nginx error logs: `sudo tail -f /var/log/nginx/error.log`
   - Verify the upstream server in Nginx configuration

### Getting Help

If you encounter issues not covered in this guide, please:
1. Check the logs: `docker-compose logs`
2. Search the issue tracker
3. Open a new issue with detailed information about the problem

---

This deployment guide is a living document. Please update it as the application evolves.

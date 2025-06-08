# =======================================
# Builder stage
# =======================================
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create static files directory (will be empty if no static files)
RUN mkdir -p staticfiles

# =======================================
# Development image
# =======================================
FROM python:3.11-slim AS development

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ffmpeg \
    gettext \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create django user with home directory and proper permissions
RUN mkdir -p /home/django && \
    groupadd -r django && \
    useradd -r -g django -d /home/django -s /bin/bash django && \
    chown -R django:django /home/django

# Set the working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir celery==5.3.6 kombu==5.3.6 billiard==4.2.1 vine==5.1.0 python-dotenv psutil==7.0.0 humanize==4.12.3

# Create and set permissions for whisper cache directory
RUN mkdir -p /tmp/whisper-cache && \
    chown -R django:django /tmp/whisper-cache && \
    chmod 777 /tmp/whisper-cache && \
    mkdir -p /home/django/.cache/whisper && \
    chown -R django:django /home/django/.cache && \
    chmod 777 /home/django/.cache/whisper

# Ensure Celery is in PATH
ENV PATH="/usr/local/bin:${PATH}"
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Copy application code
COPY --chown=django:django . .

# Set the working directory to the Django project
WORKDIR /app/app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=app.settings.local \
    PYTHONFAULTHANDLER=1

# Copy entrypoint script
COPY --chown=django:django docker/entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Create necessary directories and set permissions
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R django:django /app

# Switch to non-root user
USER django

# Expose the port the app runs on
EXPOSE 8000

# Add Python user base bin to PATH
ENV PATH="/home/django/.local/bin:${PATH}"

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Command to run the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# =======================================
# Production image
# =======================================
FROM python:3.11-slim AS production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ffmpeg \
    gettext \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create django user with home directory and proper permissions
RUN mkdir -p /home/django && \
    groupadd -r django && \
    useradd -r -g django -d /home/django -s /bin/bash django && \
    chown -R django:django /home/django

# Set the working directory
WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=django:django . .

# Set the working directory to the Django project
WORKDIR /app/app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=app.settings.production \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONPATH="/app:${PYTHONPATH}"

# Collect static files
RUN python manage.py collectstatic --noinput || echo "No static files to collect"

# Copy entrypoint script
COPY --chown=django:django docker/entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Create necessary directories and set permissions
RUN mkdir -p /app/staticfiles /app/media /home/django/.cache/whisper && \
    chown -R django:django /app /home/django/.cache

# Switch to non-root user
USER django

# Expose the port the app runs on
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "120", "app.wsgi:application"]

# =======================================
# Final stage - Default to development
# =======================================
FROM development AS final

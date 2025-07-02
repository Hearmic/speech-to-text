# Development stage
FROM python:3.11-slim AS development

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    DEBIAN_FRONTEND=noninteractive

# Install essential build dependencies first
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        gcc \
        g++ \
        make \
        cmake \
        pkg-config \
        git \
        libssl-dev \
        libffi-dev \
        libsndfile1 \
        libsndfile1-dev \
        sox \
        libsox-fmt-mp3 \
        libavcodec-extra \
        libavformat-dev \
        libavutil-dev \
        libavfilter-dev \
        libavdevice-dev \
        libflac-dev \
        libvorbis-dev \
        libmp3lame-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libxmlsec1-openssl \
        libopenblas64-0 \
        libcairo2 \
        libcairo2-dev \
        ffmpeg \
        portaudio19-dev \
        swig \
        libpulse-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies with specific versions
RUN pip install --no-cache-dir --upgrade pip==23.3.2 && \
    # Install PyTorch with CPU support first
    pip install --no-cache-dir torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu && \
    # Install numpy first as it's a dependency for many packages
    pip install --no-cache-dir numpy==1.24.3 && \
    # Install Cython and setuptools before other packages
    pip install --no-cache-dir Cython==3.0.5 setuptools==68.2.2 && \
    # Install requirements in batches to handle dependencies better
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /var/log/django \
    && chown -R 1000:1000 /app /var/log/django \
    && chmod -R 755 /var/log/django

# Create non-root user and switch to it
RUN useradd -u 1000 -d /app appuser \
    && chown -R appuser:appuser /app /var/log/django

# Switch to non-root user
USER appuser

# Set environment variables
ENV PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=app.settings.base \
    DEBUG=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--worker-class", "gthread", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "app.wsgi:application"]

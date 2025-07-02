"""
Development settings for the Speech to Text application.
"""
import os
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-dev-key-change-this-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# File upload settings - set to 0 for no limit
DATA_UPLOAD_MAX_MEMORY_SIZE = 0  # No limit on memory uploads
FILE_UPLOAD_MAX_MEMORY_SIZE = 0  # No limit on file size
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240  # Higher than the default 1000
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'speech2text'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'https://localhost',
    'http://127.0.0.1:8000',
    'https://127.0.0.1',
]

# CSRF settings
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'https://localhost',
    'http://127.0.0.1:8000',
    'https://127.0.0.1',
]

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Development settings
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Security settings for development - HTTPS disabled
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Disable static file hashing in development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Disable manifest storage in development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Disable static file finders that try to use manifest
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

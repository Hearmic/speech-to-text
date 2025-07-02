import os
from .base import *  # noqa

# Import development settings by default
if os.getenv('DJANGO_ENV') != 'production':
    try:
        from .development import *  # noqa
    except ImportError:
        pass

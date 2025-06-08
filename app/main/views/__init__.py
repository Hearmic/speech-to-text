# This file makes the views directory a Python package
# Import views directly from their modules to avoid circular imports
from .views import home, custom_404

__all__ = ['home', 'custom_404']

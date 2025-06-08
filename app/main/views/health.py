from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class HealthCheckView(View):
    """
    Health check endpoint that verifies the status of the application and its dependencies.
    Returns 200 if all dependencies are healthy, 503 otherwise.
    """
    
    def get(self, request, *args, **kwargs):
        checks = {
            'database': self.check_database(),
            'cache': self.check_cache(),
            'storage': self.check_storage(),
        }
        
        status = 200 if all(checks.values()) else 503
        return JsonResponse({
            'status': 'healthy' if status == 200 else 'unhealthy',
            'checks': checks
        }, status=status)
    
    def check_database(self):
        """Check if the database is accessible."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    def check_cache(self):
        """Check if the cache is accessible."""
        try:
            cache.set('health_check', 'ok', 5)
            return cache.get('health_check') == 'ok'
        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return False
    
    def check_storage(self):
        """Check if storage is writable."""
        try:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            test_content = b'test_content'
            path = 'health_check_test.txt'
            
            # Write test file
            default_storage.save(path, ContentFile(test_content))
            
            # Read test file
            if default_storage.exists(path):
                with default_storage.open(path) as f:
                    content = f.read()
                # Clean up
                default_storage.delete(path)
                return content == test_content
            return False
        except Exception as e:
            logger.error(f"Storage health check failed: {str(e)}")
            return False

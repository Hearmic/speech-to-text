"""
Health check endpoints for monitoring the application.
"""
import logging
from datetime import datetime
from http import HTTPStatus

from django.conf import settings
from django.core.cache import cache
from django.db import connections, DatabaseError
from django.http import JsonResponse
from django.views import View
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class HealthCheckView(View):
    """
    Health check endpoint that verifies the status of the application and its dependencies.
    """
    def get(self, request, *args, **kwargs):
        """
        Handle GET request to health check endpoint.
        
        Returns:
            JsonResponse: JSON response with health check status and details.
        """
        # Default response data
        response_data = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        # Check database connection
        db_status = self._check_database()
        response_data['checks']['database'] = db_status
        
        # Check cache (Redis) connection
        cache_status = self._check_cache()
        response_data['checks']['cache'] = cache_status
        
        # Check if any critical checks failed
        if not all(check['status'] == 'healthy' for check in response_data['checks'].values()):
            response_data['status'] = 'unhealthy'
            
        # Set appropriate status code
        status_code = (
            HTTPStatus.OK if response_data['status'] == 'healthy' 
            else HTTPStatus.SERVICE_UNAVAILABLE
        )
        
        return JsonResponse(response_data, status=status_code)
    
    def _check_database(self):
        """Check if the database is accessible."""
        try:
            connections['default'].ensure_connection()
            return {
                'status': 'healthy',
                'database': settings.DATABASES['default']['NAME'],
                'backend': settings.DATABASES['default']['ENGINE'].split('.')[-1],
            }
        except DatabaseError as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'database': settings.DATABASES['default'].get('NAME', 'unknown'),
                'backend': settings.DATABASES['default'].get('ENGINE', 'unknown').split('.')[-1],
            }
    
    def _check_cache(self):
        """Check if the cache (Redis) is accessible."""
        try:
            # Test Redis connection
            redis = Redis.from_url(settings.CACHES['default']['LOCATION'])
            redis.ping()
            return {
                'status': 'healthy',
                'backend': 'redis',
                'location': settings.CACHES['default']['LOCATION'].split('@')[-1],
            }
        except (RedisError, KeyError, AttributeError) as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'backend': 'unknown',
            }


def health_check(request):
    """Simple health check endpoint that returns a 200 OK response.
    
    This is useful for load balancers and container orchestration systems
    that need a simple endpoint to check if the application is running.
    """
    return JsonResponse({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
    })

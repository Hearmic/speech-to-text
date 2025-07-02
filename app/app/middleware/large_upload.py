"""
Middleware to handle large file uploads for superusers.
"""
from django.conf import settings
from django.core.exceptions import RequestDataTooBig

class LargeUploadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.superuser_max_size = getattr(settings, 'SUPERUSER_UPLOAD_MAX_MEMORY_SIZE', 0)  # 0 means no limit

    def __call__(self, request):
        # Only modify settings for superusers
        if hasattr(request, 'user') and request.user.is_superuser:
            # Save original settings
            original_data_upload = settings.DATA_UPLOAD_MAX_MEMORY_SIZE
            original_file_upload = settings.FILE_UPLOAD_MAX_MEMORY_SIZE
            
            # Apply superuser limits
            if self.superuser_max_size > 0:
                settings.DATA_UPLOAD_MAX_MEMORY_SIZE = self.superuser_max_size
                settings.FILE_UPLOAD_MAX_MEMORY_SIZE = self.superuser_max_size
            else:
                # Use a very large number for superusers (effectively no limit)
                settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024 * 10  # 10GB
                settings.FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024 * 10  # 10GB
        
        try:
            response = self.get_response(request)
            return response
        except RequestDataTooBig:
            if hasattr(request, 'user') and request.user.is_superuser:
                # If superuser still hits the limit, it's a real error
                raise
            # For regular users, show a more helpful error message
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden(
                "File too large. Please contact an administrator for assistance with large files."
            )
        finally:
            # Restore original settings
            if hasattr(request, 'user') and request.user.is_superuser:
                settings.DATA_UPLOAD_MAX_MEMORY_SIZE = original_data_upload
                settings.FILE_UPLOAD_MAX_MEMORY_SIZE = original_file_upload

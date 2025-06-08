"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf.urls import handler404

# Import views directly to avoid circular imports
from main.views.views import home
from main.views.health import HealthCheckView

urlpatterns = [
    # Health check
    path('health/', HealthCheckView.as_view(), name='health_check'),
    
    # Django app
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    
    # Authentication URLs
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Audio app URLs
    path('audio/', include('audio.urls', namespace='audio')),
    
    # Include API URLs - temporarily disabled
    # path('api/', include('api.urls')),
]

# Custom error handlers
handler404 = 'main.views.custom_404'

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

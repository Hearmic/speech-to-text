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
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect

from main.views.views import home
from main.views.health import HealthCheckView

urlpatterns = [
    # Health check
    path('health/', HealthCheckView.as_view(), name='health_check'),
    
    # Main app URLs
    path('', include('main.urls', namespace='main')),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication and User Management URLs
    path('accounts/', include('users.urls')),  # Custom user URLs (profile, etc.)
    path('accounts/', include('allauth.urls')),  # Allauth URLs (login, signup, etc.)
    
    # Audio app URLs
    path('audio/', include('audio.urls', namespace='audio')),
    
    # Include API URLs - temporarily disabled
    # path('api/', include('api.urls')),
]

# Custom error handlers
handler400 = 'main.views.custom_400'
handler403 = 'main.views.custom_403'
handler404 = 'main.views.custom_404'
handler500 = 'main.views.custom_500'

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""
Custom context processors for the main app.
"""
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse

def site_info(request):
    """
    Add site information to the template context.
    """
    current_site = get_current_site(request)
    return {
        'SITE_NAME': current_site.name,
        'SITE_DOMAIN': current_site.domain,
        'CONTACT_EMAIL': getattr(settings, 'CONTACT_EMAIL', 'contact@example.com'),
        'DEBUG': settings.DEBUG,
        'GOOGLE_ANALYTICS_ID': getattr(settings, 'GOOGLE_ANALYTICS_ID', None),
    }

def navigation_links(request):
    """
    Add navigation links to the template context.
    """
    nav_links = [
        {'name': 'Home', 'url': reverse('main:home'), 'icon': 'house'},
    ]
    
    if request.user.is_authenticated:
        nav_links.extend([
            {'name': 'Transcriptions', 'url': reverse('audio:audio_list'), 'icon': 'collection'},
            {'name': 'New Transcription', 'url': reverse('audio:upload_audio'), 'icon': 'upload'},
        ])
    
    nav_links.extend([
        {'name': 'Pricing', 'url': reverse('main:pricing'), 'icon': 'tags'},
        {'name': 'Contact', 'url': reverse('main:contact'), 'icon': 'envelope'},
    ])
    
    return {'nav_links': nav_links}

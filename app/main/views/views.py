from django.shortcuts import render
from django.template import RequestContext, TemplateDoesNotExist
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME
from django.template.loader import render_to_string
from django.http import HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest

def home(request):
    """
    Home view that displays the main dashboard or landing page.
    """
    # Get the first 3 active plans for the features section
    from subscriptions.models import SubscriptionPlan
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')[:3]
    
    context = {
        'plans': plans,
        'features': [
            'High accuracy speech-to-text conversion',
            'Support for multiple audio formats',
            'Speaker diarization',
            'Easy-to-use interface',
            'Secure file handling',
            'API access available',
        ]
    }
    
    return render(request, 'main/landing.html', context)


def custom_400(request, exception=None):
    """
    Custom 400 error handler.
    """
    return render(request, 'main/errors/400.html', status=400)


def custom_403(request, exception=None):
    """
    Custom 403 error handler.
    """
    return render(request, 'main/errors/403.html', status=403)


def custom_404(request, exception=None):
    """
    Custom 404 error handler.
    """
    return render(request, 'main/errors/404.html', status=404)


def custom_500(request):
    """
    Custom 500 error handler.
    """
    try:
        return render(request, 'main/errors/500.html', status=500)
    except TemplateDoesNotExist:
        # Fallback to Django's default 500 template if ours is missing
        return HttpResponseServerError(
            render_to_string(ERROR_500_TEMPLATE_NAME),
            content_type='text/html'
        )


@requires_csrf_token
def csrf_failure(request, reason=""):
    """
    Custom CSRF failure view.
    """
    return render(request, 'main/errors/403_csrf.html', status=403)

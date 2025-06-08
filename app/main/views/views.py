from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.urls import reverse

def home(request):
    """
    Home view that redirects to the landing page.
    """
    if request.user.is_authenticated:
        return redirect('audio:audio_list')
    return render(request, 'landing.html')


def custom_404(request, exception=None):
    """
    Custom 404 error handler.
    """
    return render(request, '404.html', status=404)

from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from allauth.account import views as allauth_views
from . import views

app_name = 'users'

urlpatterns = [
    # Profile
    path('profile/', views.profile, name='profile'),
    
    # Include allauth URLs
    path('', include('allauth.urls')),
    
    # Password reset views (customize these if needed)
    path('password/change/', 
         allauth_views.PasswordChangeView.as_view(
             template_name='users/account/password_change.html'
         ), 
         name='account_change_password'),
    path('password/set/', 
         allauth_views.PasswordSetView.as_view(
             template_name='users/account/password_set.html'
         ), 
         name='account_set_password'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
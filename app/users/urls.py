from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'users'

urlpatterns = [
    # Profile
    path('profile/', views.profile, name='profile'),
    
    # Include allauth URLs
    path('', include('allauth.urls')),
    
    # Password reset views (customize these if needed)
    path('password/change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='users/account/password_change.html'
         ), 
         name='account_change_password'),
    path('password/set/', 
         auth_views.PasswordSetView.as_view(
             template_name='users/account/password_set.html'
         ), 
         name='account_set_password'),
    path('password/reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='users/account/password_reset.html',
             email_template_name='users/account/email/password_reset_email.html',
             subject_template_name='users/account/email/password_reset_subject.txt'
         ), 
         name='account_reset_password'),
    path('password/reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/account/password_reset_done.html'
         ), 
         name='account_reset_password_done'),
    path('password/reset/confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/account/password_reset_from_key.html'
         ), 
         name='account_reset_password_from_key'),
    path('password/reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/account/password_reset_from_key_done.html'
         ), 
         name='account_reset_password_from_key_done'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
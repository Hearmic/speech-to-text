from django.urls import path
from django.urls import re_path
from . import views
from django.views.decorators.csrf import csrf_exempt

app_name = 'audio'

urlpatterns = [
    path('', views.audio_list, name='audio_list'),
    path('upload/', views.upload_audio, name='upload_audio'),
    path('<uuid:pk>/', views.audio_detail, name='audio_detail'),
    path('<uuid:pk>/delete/', views.delete_audio, name='delete_audio'),
    path('<uuid:pk>/status/', views.check_audio_status, name='check_audio_status'),
    path('check-model-availability/', views.check_model_availability, name='check_model_availability'),
]

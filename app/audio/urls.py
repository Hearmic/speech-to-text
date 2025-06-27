from django.urls import path
from django.urls import re_path
from . import views
from .views.speaker_diarization import process_speaker_diarization
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.views import obtain_auth_token

app_name = 'audio'

urlpatterns = [
    path('', views.audio_list, name='audio_list'),
    path('upload/', views.upload_audio, name='upload_audio'),
    path('<uuid:pk>/', views.audio_detail, name='audio_detail'),
    path('<uuid:pk>/delete/', views.delete_audio, name='delete_audio'),
    path('<uuid:pk>/status/', views.check_audio_status, name='check_audio_status'),
    path('check-model-availability/', views.check_model_availability, name='check_model_availability'),
    
    # API endpoints
    path('api/token/', obtain_auth_token, name='api_token'),
    path('api/transcriptions/<uuid:transcription_id>/diarize/', 
         process_speaker_diarization, 
         name='process_speaker_diarization'),
]

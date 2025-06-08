import os
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, FileResponse, Http404, HttpResponse
from django.views.decorators.http import require_http_methods, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files import File
import tempfile
import mimetypes
from pathlib import Path
from django.views.decorators.http import require_GET
from django.http import HttpResponse
from django.conf import settings

from .models import Transcription as Audio, AudioFile
from .forms import AudioUploadForm

def get_file_type(file_name):
    """Determine if the file is a video or audio based on its extension"""
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    ext = Path(file_name).suffix.lower()
    return 'video' if ext in video_extensions else 'audio'

@login_required
def upload_audio(request):
    if request.method == 'POST':
        form = AudioUploadForm(request.POST, request.FILES, user=request.user)
        # The form's clean method will validate the model selection
        if form.is_valid():
            try:
                transcription = form.save(commit=False)
                transcription.user = request.user
                
                # Get the uploaded file
                uploaded_file = request.FILES.get('audio_file')
                if not uploaded_file:
                    messages.error(request, 'No file was uploaded.')
                    return render(request, 'audio/upload.html', {'form': form})
                
                # Check file size (limit to 500MB)
                max_size = 500 * 1024 * 1024  # 500MB
                if uploaded_file.size > max_size:
                    messages.error(request, 'File is too large. Maximum allowed size is 500MB.')
                    return render(request, 'audio/upload.html', {'form': form})
                
                # Check file type
                file_type = get_file_type(uploaded_file.name)
                
                # Save the transcription first
                transcription.save()
                
                try:
                    # Save the file to the media directory
                    file_path = os.path.join('audio_uploads', str(request.user.id), uploaded_file.name)
                    file_path = default_storage.save(file_path, ContentFile(uploaded_file.read()))
                    
                    # Create AudioFile instance
                    audio_file = AudioFile(
                        transcription=transcription,
                        file=file_path,
                        duration=0,  # Will be updated during processing
                        file_size=uploaded_file.size
                    )
                    audio_file.save()
                    
                    # Start processing the file
                    transcription.process_audio()
                    
                    messages.success(
                        request, 
                        f'Your {file_type} file has been uploaded and is being processed. '
                        'You will be notified when processing is complete.'
                    )
                    return redirect('audio:audio_list')
                    
                except Exception as e:
                    # Clean up if something goes wrong
                    if 'audio_file' in locals() and audio_file.file:
                        if default_storage.exists(audio_file.file.name):
                            default_storage.delete(audio_file.file.name)
                    transcription.delete()
                    raise e
                    
            except Exception as e:
                messages.error(
                    request, 
                    f'An error occurred while processing your {file_type} file. Please try again.'
                )
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing {file_type} file: {str(e)}", exc_info=True)
                return render(request, 'audio/upload.html', {'form': form})
    else:
        print(f"Creating form for user: {request.user}")
        form = AudioUploadForm(user=request.user)
        print(f"Form created with user: {request.user}")
    
    # Debug info
    debug_info = {
        'user': str(request.user),
        'is_authenticated': request.user.is_authenticated,
        'has_subscription': hasattr(request.user, 'subscription') and request.user.subscription is not None,
        'user_attrs': dir(request.user) if hasattr(request.user, '__dict__') else 'No __dict__'
    }
    
    return render(request, 'audio/upload.html', {
        'form': form, 
        'debug_user': str(request.user),
        'debug_info': debug_info
    })

@login_required
def audio_list(request):
    audios = Audio.objects.select_related('audio_file').filter(user=request.user).order_by('-created_at')
    return render(request, 'audio/list.html', {'audios': audios})

@login_required
def audio_detail(request, pk):
    audio = get_object_or_404(Audio, pk=pk, user=request.user)
    file_type = 'video' if audio.audio_file and any(ext in str(audio.audio_file.file).lower() for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']) else 'audio'
    return render(request, 'audio/detail.html', {
        'audio': audio,
        'file_type': file_type,
        'is_video': file_type == 'video',
        'MEDIA_URL': settings.MEDIA_URL  # Add MEDIA_URL to the template context
    })

@login_required
@require_http_methods(['DELETE'])
def delete_audio(request, pk):
    audio = get_object_or_404(Audio, pk=pk, user=request.user)
    
    # Delete the audio file from storage
    if audio.audio_file:
        if os.path.isfile(audio.audio_file.path):
            os.remove(audio.audio_file.path)
    
    # Delete the database record
    audio.delete()
    
    messages.success(request, 'Audio file has been deleted.')
    return JsonResponse({'status': 'success'})

@login_required
def check_audio_status(request, pk):
    audio = get_object_or_404(Audio, pk=pk, user=request.user)
    return JsonResponse({
        'status': audio.status,
        'text': audio.text or '',
        'is_ready': audio.status == 'completed'
    })

@require_GET
def check_model_availability(request):
    """HTMX endpoint to check if a model is available for the user's subscription."""
    if not request.user.is_authenticated or not hasattr(request.user, 'subscription'):
        return HttpResponse(status=200)  # Default to base model for non-authenticated users
    
    model = request.GET.get('model', 'base')
    available_models = request.user.subscription.plan.available_models
    
    if model not in available_models:
        return HttpResponse(
            '<div class="alert alert-warning small p-2 mb-0">' \
            '<i class="bi bi-exclamation-triangle-fill me-1"></i> ' \
            'This model requires a higher subscription tier.' \
            '</div>'
        )
    return HttpResponse('')

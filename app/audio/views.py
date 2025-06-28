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

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.core.files.storage import default_storage
from django.conf import settings
from pathlib import Path

from .models import Transcription, MediaFile
from .forms import AudioUploadForm

logger = logging.getLogger(__name__)

def get_file_type(file_name):
    """
    Determine if the file is a video or audio based on its extension
    Returns: 'video', 'audio', or None if not supported
    """
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.3gp'}
    audio_extensions = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.wma', '.aiff'}
    
    ext = Path(file_name).suffix.lower()
    if ext in video_extensions:
        return 'video'
    elif ext in audio_extensions:
        return 'audio'
    return None

@login_required
def upload_audio(request):
    """Handle file uploads for both audio and video files"""
    if request.method == 'POST':
        form = AudioUploadForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            try:
                # Start transaction to ensure data consistency
                with transaction.atomic():
                    # Create the transcription record
                    transcription = form.save(commit=False)
                    transcription.user = request.user
                    transcription.save()
                    
                    # Get the uploaded file
                    uploaded_file = request.FILES.get('audio_file')
                    if not uploaded_file:
                        messages.error(request, 'No file was uploaded.')
                        return render(request, 'audio/upload.html', {'form': form})
                    
                    # Check file type
                    file_type = get_file_type(uploaded_file.name)
                    if not file_type:
                        messages.error(request, 'Unsupported file format. Please upload a valid audio or video file.')
                        return render(request, 'audio/upload.html', {'form': form})
                    
                    # Check file size based on subscription (default max 500MB)
                    max_size = 500 * 1024 * 1024  # 500MB default
                    if hasattr(request.user, 'subscription') and request.user.subscription:
                        max_size = request.user.subscription.max_file_size_mb * 1024 * 1024
                    
                    if uploaded_file.size > max_size:
                        messages.error(
                            request, 
                            f'File is too large. Maximum allowed size is {max_size // (1024 * 1024)}MB.'
                        )
                        return render(request, 'audio/upload.html', {'form': form})
                    
                    # Create media file record
                    media_file = MediaFile(
                        transcription=transcription,
                        original_file=uploaded_file,
                        is_video=(file_type == 'video')
                    )
                    media_file.save()
                    
                    # If it's a video, extract audio asynchronously
                    if media_file.is_video:
                        from .tasks import extract_audio_task
                        extract_audio_task.delay(media_file.id)
                    
                    # Start audio processing
                    transcription.process_audio()
                    
                    messages.success(request, 'Your file has been uploaded and is being processed.')
                    return redirect('audio:detail', pk=transcription.pk)
                    
            except Exception as e:
                logger.error(f"Error processing upload: {str(e)}", exc_info=True)
                messages.error(request, 'An error occurred while processing your upload. Please try again.')
                
                # Clean up any partially created objects
                if 'transcription' in locals() and transcription.pk:
                    if hasattr(transcription, 'media_file'):
                        transcription.media_file.delete()
                    transcription.delete()
                    
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = AudioUploadForm(user=request.user)
    
    # Get max file size from user's subscription or use default
    max_size_mb = 500  # Default max size in MB
    if hasattr(request.user, 'subscription') and request.user.subscription:
        max_size_mb = request.user.subscription.max_file_size_mb
    
    return render(request, 'audio/upload.html', {
        'form': form,
        'max_size_mb': max_size_mb,
    })

@login_required
def audio_list(request):
    """Display list of user's transcriptions"""
    transcriptions = Transcription.objects.filter(user=request.user).select_related('media_file').order_by('-created_at')
    return render(request, 'audio/audio_list.html', {
        'audios': transcriptions,
    })

@login_required
def audio_detail(request, pk):
    """Display details of a specific transcription"""
    audio = get_object_or_404(Transcription.objects.select_related('media_file'), pk=pk, user=request.user)
    
    # Check if the transcription is completed and has text
    if audio.status == 'completed' and not audio.text:
        audio.status = 'failed'
        audio.save(update_fields=['status'])
        messages.warning(request, 'Transcription completed but no text was generated.')
    
    # Get the appropriate file for playback (original audio or extracted audio from video)
    media_file = getattr(audio, 'media_file', None)
    playback_file = None
    if media_file:
        playback_file = media_file.get_audio_file()
    
    return render(request, 'audio/audio_detail.html', {
        'audio': audio,
        'media_file': media_file,
        'playback_file': playback_file,
    })

@login_required
@require_http_methods(['DELETE'])
def delete_audio(request, pk):
    """Delete a transcription and its associated media files"""
    audio = get_object_or_404(Transcription, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            # This will delete the transcription and associated media files through model's delete method
            audio.delete()
            messages.success(request, 'Transcription and associated media files deleted successfully.')
            return redirect('audio:list')
        except Exception as e:
            logger.error(f"Error deleting transcription {pk}: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while deleting the transcription.')
            return redirect('audio:detail', pk=pk)
    
    return render(request, 'audio/audio_confirm_delete.html', {'audio': audio})

@login_required
def check_audio_status(request, pk):
    audio = get_object_or_404(Transcription, pk=pk, user=request.user)
    return JsonResponse({
        'status': audio.status,
        'text': audio.text or '',
        'is_ready': audio.status == 'completed'
    })

@require_GET
def check_model_availability(request):
    """
    HTMX endpoint to check if a model is available for the user's subscription.
    Returns HTML response indicating model availability.
    """
    model_name = request.GET.get('model_name')
    if not model_name:
        return HttpResponseBadRequest("Model name is required")
    
    # Default to True if user is not authenticated (will be handled by login_required in the form)
    if not request.user.is_authenticated:
        return HttpResponse("<div class='text-success'><i class='bi bi-check-circle-fill'></i> Available</div>")
    
    # Get the user's subscription tier
    subscription = getattr(request.user, 'subscription', None)
    
    # Map model names to their required subscription tiers
    model_requirements = {
        'tiny': 'free',
        'base': 'free',
        'small': 'basic',
        'medium': 'pro',
        'large': 'enterprise',
    }
    
    required_tier = model_requirements.get(model_name.lower(), 'enterprise')
    
    # If no subscription, only allow free models
    if not subscription or subscription.tier == 'free':
        is_available = required_tier == 'free'
    # For paid subscriptions, check if the model is allowed
    else:
        # This is a simplified check - you might want to implement a more robust comparison
        subscription_tiers = ['free', 'basic', 'pro', 'enterprise']
        is_available = subscription_tiers.index(subscription.tier.lower()) >= subscription_tiers.index(required_tier)
    
    if is_available:
        return HttpResponse("<div class='text-success'><i class='bi bi-check-circle-fill'></i> Available</div>")
    else:
        return HttpResponse(f"<div class='text-danger'><i class='bi bi-x-circle-fill'></i> Requires {required_tier.capitalize()} plan or higher</div>")

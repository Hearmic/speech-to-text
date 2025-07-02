import logging
import tempfile
import mimetypes
from pathlib import Path
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, FileResponse, Http404, HttpResponse
from django.views.decorators.http import require_http_methods, require_GET
from django.urls import reverse
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files import File
from django.utils import timezone
from subscriptions.models import UserSubscription, SubscriptionPlan

from .models import Transcription, MediaFile
from .forms import AudioUploadForm
from .diarization import SpeakerDiarizer, DIARIZATION_AVAILABLE
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

# Initialize diarizer
diarizer = None
if DIARIZATION_AVAILABLE:
    try:
        diarizer = SpeakerDiarizer()
        if not diarizer.is_available():
            logger.warning("Speaker diarization is not available")
    except Exception as e:
        logger.error(f"Failed to initialize speaker diarizer: {e}")

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
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        form = AudioUploadForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            try:
                # Log form data for debugging
                logger.info(f"Form is valid. Processing upload for user: {request.user.email}")
                logger.info(f"Model choices: {form.fields['model'].choices}")
                logger.info(f"Form fields: {form.fields.keys()}")
                
                # Start transaction to ensure data consistency
                with transaction.atomic():
                    # Create the transcription record
                    transcription = form.save(commit=False)
                    transcription.user = request.user
                    transcription.status = 'pending'  # Set initial status
                    transcription.save()
                    
                    # Get the uploaded file
                    uploaded_file = request.FILES.get('audio_file')
                    if not uploaded_file:
                        messages.error(request, 'No file was uploaded.')
                        return render(request, 'audio/upload.html', {'form': form})
                    
                    # Log file info
                    logger.info(f"Processing file: {uploaded_file.name}, size: {uploaded_file.size} bytes")
                    
                    # Check file type
                    file_type = get_file_type(uploaded_file.name)
                    if not file_type:
                        error_msg = f'Unsupported file format: {uploaded_file.name}. Please upload a valid audio or video file.'
                        logger.warning(error_msg)
                        messages.error(request, error_msg)
                        return render(request, 'audio/upload.html', {'form': form})
                    
                    # Check file size based on subscription
                    try:
                        subscription = UserSubscription.objects.get(
                            user=request.user, 
                            status=UserSubscription.STATUS_ACTIVE
                        )
                        max_size_mb = subscription.plan.max_audio_minutes * 60  # Convert minutes to seconds for calculation
                        max_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
                        
                        if uploaded_file.size > max_size:
                            error_msg = f'File is too large ({uploaded_file.size/1024/1024:.2f}MB). Maximum allowed size is {max_size_mb}MB with your current plan.'
                            logger.warning(error_msg)
                            messages.error(request, error_msg)
                            return render(request, 'audio/upload.html', {'form': form})
                            
                    except UserSubscription.DoesNotExist:
                        error_msg = 'You need an active subscription to upload files.'
                        logger.warning(f"User {request.user.email} attempted to upload without an active subscription")
                        messages.error(request, error_msg)
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
                    return redirect('audio:audio_detail', pk=transcription.pk)
                    
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
    
    # Get max file size from user's subscription
    try:
        subscription = UserSubscription.objects.get(
            user=request.user,
            status=UserSubscription.STATUS_ACTIVE
        )
        max_size_mb = subscription.plan.max_audio_minutes * 60  # Convert minutes to MB
    except UserSubscription.DoesNotExist:
        max_size_mb = 30  # Default to 30MB for non-subscribed users
        
    return render(request, 'audio/upload.html', {
        'form': form,
        'max_size_mb': max_size_mb,
    })

@login_required
def audio_list(request):
    """Display list of user's transcriptions"""
    transcriptions = Transcription.objects.filter(user=request.user).select_related('media_file').order_by('-created_at')
    
    # Get subscription status
    has_active_subscription = False
    try:
        subscription = UserSubscription.objects.get(
            user=request.user,
            status=UserSubscription.STATUS_ACTIVE
        )
        has_active_subscription = True
    except UserSubscription.DoesNotExist:
        pass
    
    return render(request, 'audio/audio_list.html', {
        'audios': transcriptions,
        'has_active_subscription': has_active_subscription,
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
    
    # Get the media file and set it as audio_file for template compatibility
    media_file = getattr(audio, 'media_file', None)
    playback_file = None
    if media_file:
        playback_file = media_file.get_audio_file()
    
    return render(request, 'audio/audio_detail.html', {
        'audio': audio,
        'media_file': media_file,
        'playback_file': playback_file,
        # For backward compatibility with the template
        'audio_file': media_file,
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
    model_name = request.GET.get('model', '').lower()
    user = request.user
    
    # Default response for unauthenticated users
    if not user.is_authenticated:
        return HttpResponse(
            '<span class="text-danger">Please log in to check model availability</span>',
            content_type='text/html'
        )
    
    try:
        # Get the user's subscription
        subscription = UserSubscription.objects.get(user=user, status=UserSubscription.STATUS_ACTIVE)
        plan = subscription.plan
        
        # Check if the model is supported by the plan
        if model_name in plan.supported_models:
            return HttpResponse(
                '<span class="text-success"><i class="bi bi-check-circle-fill"></i> Available with your plan</span>',
                content_type='text/html'
            )
        else:
            return HttpResponse(
                f'<span class="text-warning"><i class="bi bi-exclamation-triangle-fill"></i> Not available with your {plan.name} plan. Please upgrade.</span>',
                content_type='text/html'
            )
            
    except UserSubscription.DoesNotExist:
        return HttpResponse(
            '<span class="text-warning">No active subscription found</span>',
            content_type='text/html'
        )
    except Exception as e:
        logger.error(f"Error checking model availability: {str(e)}", exc_info=True)
        return HttpResponse(
            '<span class="text-danger"><i class="bi bi-x-circle-fill"></i> Error checking availability</span>',
            content_type='text/html'
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_speaker_diarization(request, transcription_id):
    """
    Process speaker diarization for a transcription
    
    This endpoint is protected and only available to authenticated users with
    an active subscription that includes speaker diarization.
    """
    # Check if diarization is available
    if not DIARIZATION_AVAILABLE or diarizer is None:
        return Response(
            {"error": "Speaker diarization is not available on this server"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    # Get the transcription
    transcription = get_object_or_404(
        Transcription,
        id=transcription_id,
        user=request.user  # Ensure user owns the transcription
    )
    
    try:
        # Get the user's active subscription
        subscription = UserSubscription.objects.get(
            user=request.user, 
            status=UserSubscription.STATUS_ACTIVE
        )
        
        # Check if the plan includes speaker diarization
        if not subscription.plan.speaker_diarization_enabled:
            return Response(
                {"error": "Your current plan does not include speaker diarization"},
                status=status.HTTP_403_FORBIDDEN
            )
            
    except UserSubscription.DoesNotExist:
        return Response(
            {"error": "This feature requires an active subscription"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if diarization was already performed
    if transcription.has_speaker_diarization:
        return Response(
            {
                "status": "already_processed",
                "message": "Speaker diarization was already performed on this transcription"
            },
            status=status.HTTP_200_OK
        )
    
    try:
        # Get the audio file path
        if not hasattr(transcription, 'media_file') or not hasattr(transcription.media_file, 'file'):
            return Response(
                {"error": "Audio file not found for this transcription"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        audio_path = transcription.media_file.file.path
        
        # Run diarization
        diarization_result = diarizer.process_audio_file(audio_path)
        
        if not diarization_result:
            return Response(
                {"error": "Failed to process speaker diarization"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Update transcription with diarization data
        transcription.has_speaker_diarization = True
        transcription.speakers = diarization_result.speakers
        transcription.speaker_segments = diarization_result.segments
        
        # If we have speaker segments, update the main segments with speaker info
        if diarization_result.segments and hasattr(transcription, 'segments'):
            from .diarization import merge_transcription_with_diarization
            
            # Merge diarization with existing segments
            merged_segments = merge_transcription_with_diarization(
                transcription.segments or [],
                diarization_result.segments
            )
            
            # Update the segments with speaker information
            transcription.segments = merged_segments
        
        # Save the transcription
        transcription.save(update_fields=[
            'has_speaker_diarization',
            'speakers',
            'speaker_segments',
            'segments',
            'updated_at'
        ])
        
        return Response({
            "status": "success",
            "message": "Speaker diarization completed successfully",
            "speaker_count": len(diarization_result.speakers),
            "segment_count": len(diarization_result.segments)
        })
    
    except Exception as e:
        logger.error(f"Error during speaker diarization: {e}", exc_info=True)
        return Response(
            {"error": f"An error occurred during speaker diarization: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

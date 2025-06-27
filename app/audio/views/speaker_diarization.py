import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from ..models import Transcription
from ..diarization import SpeakerDiarizer, DIARIZATION_AVAILABLE

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
    
    # Check if user has an active subscription with speaker diarization
    if not hasattr(request.user, 'subscription') or not hasattr(request.user.subscription, 'plan'):
        return Response(
            {"error": "This feature requires an active subscription"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if the plan includes speaker diarization
    subscription = request.user.subscription.plan
    if not hasattr(subscription, 'features') or not isinstance(subscription.features, dict) or \
       not subscription.features.get('speaker_diarization', False):
        return Response(
            {"error": "Your current plan does not include speaker diarization"},
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
        if not hasattr(transcription, 'audio_file') or not hasattr(transcription.audio_file, 'file'):
            return Response(
                {"error": "Audio file not found for this transcription"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        audio_path = transcription.audio_file.file.path
        
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
            from ..diarization import merge_transcription_with_diarization
            
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

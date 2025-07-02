from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
import json

User = get_user_model()

# Note: SubscriptionPlan and UserSubscription models have been moved to the 'subscriptions' app
# to avoid duplication and conflicts. Please use the models from the 'subscriptions' app instead.
# This file is kept for backward compatibility but will be removed in a future version.


class UserTranscription(models.Model):
    """Legacy model to store transcriptions with speaker diarization (deprecated)
    
    This model is kept for backward compatibility but should be phased out in favor of
    the more comprehensive Transcription model in the audio app.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='legacy_transcriptions')
    audio_file = models.FileField(upload_to='audio_files/')
    original_filename = models.CharField(max_length=255)
    transcription = models.TextField(blank=True, null=True)
    speaker_segments = models.JSONField(blank=True, null=True)  # Store speaker diarization data
    language = models.CharField(max_length=10, default='en')
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_speaker_transcription(self):
        """Format transcription with speaker labels"""
        if not self.speaker_segments:
            return self.transcription or ""
        
        try:
            segments = json.loads(self.speaker_segments)
            formatted = []
            
            for segment in segments:
                speaker = segment.get('speaker', 'Unknown')
                text = segment.get('text', '')
                formatted.append(f"<span class='speaker-{speaker.lower()}'>{speaker}: {text}</span>")
            
            return "\n".join(formatted)
        except (json.JSONDecodeError, AttributeError):
            return self.transcription or ""

    def __str__(self):
        return f"[Legacy] {self.original_filename} - {self.user.email}"

    class Meta:
        verbose_name = 'Legacy User Transcription'
        verbose_name_plural = 'Legacy User Transcriptions'
        ordering = ['-created_at']

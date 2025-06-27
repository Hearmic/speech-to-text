from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class SubscriptionPlan(models.Model):
    """Model for different subscription plans"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['price']


class UserSubscription(models.Model):
    """Model to track user subscriptions"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        """Check if subscription is currently active"""
        return self.is_active and timezone.now() <= self.end_date

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"


class Transcription(models.Model):
    """Model to store transcriptions with speaker diarization"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transcriptions')
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
        return f"{self.original_filename} - {self.user.email}"

    class Meta:
        ordering = ['-created_at']

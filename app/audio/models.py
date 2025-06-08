import os
import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

class Transcription(models.Model):
    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]
    
    # Whisper model choices (aligned with SubscriptionPlan)
    WHISPER_TINY = 'tiny'
    WHISPER_BASE = 'base'
    WHISPER_SMALL = 'small'
    WHISPER_MEDIUM = 'medium'
    WHISPER_LARGE = 'large'
    
    MODEL_CHOICES = [
        (WHISPER_TINY, 'Tiny (Fastest, lowest accuracy)'),
        (WHISPER_BASE, 'Base (Fast, lower accuracy)'),
        (WHISPER_SMALL, 'Small (Good balance)'),
        (WHISPER_MEDIUM, 'Medium (Better accuracy)'),
        (WHISPER_LARGE, 'Large (Best accuracy, slowest)'),
    ]
    
    # Model size to display name mapping
    MODEL_DISPLAY_NAMES = {
        WHISPER_TINY: 'Tiny (Fastest)',
        WHISPER_BASE: 'Base (Fast)',
        WHISPER_SMALL: 'Small (Balanced)',
        WHISPER_MEDIUM: 'Medium (Better)',
        WHISPER_LARGE: 'Large (Best)',
    }
    
    # Model size to required subscription level (for reference)
    MODEL_REQUIREMENTS = {
        WHISPER_TINY: 'free',
        WHISPER_BASE: 'free',
        WHISPER_SMALL: 'basic',
        WHISPER_MEDIUM: 'pro',
        WHISPER_LARGE: 'enterprise',
    }
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transcriptions')
    title = models.CharField(max_length=255, blank=True)
    
    # Transcription status and content
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    text = models.TextField(blank=True, null=True, help_text='Full transcription text')
    processing_time = models.FloatField(null=True, blank=True, help_text='Processing time in seconds')
    
    # Language information
    language = models.CharField(max_length=10, default='en', help_text='Detected language code')
    language_probability = models.FloatField(null=True, blank=True, help_text='Confidence score of detected language')
    
    # Transcription details
    word_count = models.PositiveIntegerField(null=True, blank=True, help_text='Number of words in transcription')
    segments = models.JSONField(null=True, blank=True, help_text='Detailed transcription segments with timestamps')
    
    # Model information
    model_used = models.CharField(
        max_length=10,
        choices=MODEL_CHOICES,
        default=WHISPER_BASE,
        help_text='Whisper model used for transcription'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def model_display_name(self):
        """Get the display name of the model used"""
        return self.MODEL_DISPLAY_NAMES.get(self.model_used, self.model_used.capitalize())
    
    @property
    def detected_language(self):
        """Return the full language name if available"""
        from django.conf import settings
        return dict(settings.LANGUAGES).get(self.language, self.language)
    
    @property
    def duration_minutes(self):
        """Return duration in minutes:seconds format"""
        if not self.audio_file or not self.audio_file.duration:
            return "-"
        minutes = int(self.audio_file.duration // 60)
        seconds = int(self.audio_file.duration % 60)
        return f"{minutes}:{seconds:02d}"
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title or 'Untitled'} - {self.get_status_display()}"
        
    def process_audio(self):
        """
        Start the audio processing task asynchronously
        """
        from .tasks import process_audio_task
        process_audio_task.delay(str(self.id))


def audio_file_path(instance, filename):
    """Generate file path for media files"""
    ext = os.path.splitext(filename)[1].lower()
    filename = f"{uuid.uuid4()}{ext}"
    return os.path.join('media_uploads', str(instance.transcription.user.id), filename)


def is_video_file(filename):
    """Check if the file is a video based on extension"""
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    ext = os.path.splitext(filename)[1].lower()
    return ext in video_extensions

# Alias for backward compatibility
get_upload_path = audio_file_path


class AudioFile(models.Model):
    transcription = models.OneToOneField(Transcription, on_delete=models.CASCADE, related_name='audio_file')
    file = models.FileField(
        upload_to=audio_file_path,
        validators=[
            FileExtensionValidator(allowed_extensions=[
                # Audio formats
                'mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac', 'wma', 'aiff',
                # Video formats
                'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv', 'm4v', '3gp'
            ])
        ]
    )
    is_video = models.BooleanField(default=False, editable=False)
    
    duration = models.FloatField(help_text='Duration in seconds')
    file_size = models.PositiveIntegerField(help_text='File size in bytes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        if hasattr(self, 'transcription') and self.transcription.user:
            user = self.transcription.user
            if user.subscription and user.subscription.max_audio_length:
                if self.duration > user.subscription.max_audio_length * 60:  # Convert minutes to seconds
                    raise ValidationError(
                        f'Your current plan allows audio files up to {user.subscription.max_audio_length} minutes.'
                    )
    
    def save(self, *args, **kwargs):
        # Set is_video based on file extension
        if self.file:
            self.is_video = is_video_file(self.file.name)
        
        # Validate the model
        self.full_clean()
        
        # Save the model
        super().save(*args, **kwargs)
        
        # Set the transcription title to the filename if not set
        if not self.transcription.title and self.file:
            self.transcription.title = os.path.splitext(os.path.basename(self.file.name))[0]
            self.transcription.save(update_fields=['title'])
    
    def delete(self, *args, **kwargs):
        """Delete the file from storage when the model is deleted"""
        storage, path = self.file.storage, self.file.path
        super().delete(*args, **kwargs)
        storage.delete(path)
    
    def __str__(self):
        return f"Audio file for {self.transcription}"

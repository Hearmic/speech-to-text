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
    
    # Speaker diarization
    has_speaker_diarization = models.BooleanField(default=False, help_text='Whether speaker diarization was performed')
    speakers = models.JSONField(
        null=True, 
        blank=True, 
        help_text='List of speakers with their display names and colors',
        default=list
    )
    speaker_segments = models.JSONField(
        null=True, 
        blank=True, 
        help_text='Segments with speaker information',
        default=list
    )
    
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
        if not self.media_file or not self.media_file.duration:
            return "-"
        minutes = int(self.media_file.duration // 60)
        seconds = int(self.media_file.duration % 60)
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


def get_media_upload_path(instance, filename):
    """
    Returns the upload path for media files (audio/video)
    Format: user_<user_id>/<file_type>/<year>/<month>/<filename>
    """
    file_type = 'videos' if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.3gp')) else 'audios'
    return f"user_{instance.user.id}/{file_type}/{timezone.now().strftime('%Y/%m')}/{filename}"


class MediaFile(models.Model):
    """
    Model to store both audio and video files for a transcription
    """
    transcription = models.OneToOneField(Transcription, on_delete=models.CASCADE, related_name='media_file')
    
    # Original file (video or audio)
    original_file = models.FileField(
        upload_to=get_media_upload_path,
        validators=[
            FileExtensionValidator(allowed_extensions=[
                # Audio formats
                'mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac', 'wma', 'aiff',
                # Video formats
                'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv', 'm4v', '3gp'
            ])
        ],
        help_text="Original uploaded file (video or audio)"
    )
    
    # Extracted audio (populated if original is video)
    extracted_audio = models.FileField(
        upload_to=get_media_upload_path,
        null=True,
        blank=True,
        help_text="Extracted audio file (for video uploads)"
    )
    
    # File type detection
    is_video = models.BooleanField(default=False, editable=False)
    
    # Common metadata
    duration = models.FloatField(blank=True, null=True, help_text='Duration in seconds')
    sample_rate = models.IntegerField(blank=True, null=True, help_text='Sample rate in Hz')
    channels = models.IntegerField(blank=True, null=True, help_text='Number of audio channels')
    bitrate = models.IntegerField(blank=True, null=True, help_text='Bitrate in kbps')
    
    # Video-specific metadata
    video_codec = models.CharField(max_length=50, blank=True, null=True)
    video_resolution = models.CharField(max_length=20, blank=True, null=True)
    frame_rate = models.FloatField(blank=True, null=True)
    
    # File processing status
    audio_extracted = models.BooleanField(default=False, help_text='Whether audio was extracted from video')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Media File'
        verbose_name_plural = 'Media Files'
    
    def save(self, *args, **kwargs):
        # Set is_video based on file extension if original_file exists
        if self.original_file:
            ext = os.path.splitext(self.original_file.name)[1].lower()
            self.is_video = ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.3gp']
        
        super().save(*args, **kwargs)
        
        # Set the transcription title to the filename if not set
        if not self.transcription.title and self.original_file:
            self.transcription.title = os.path.splitext(os.path.basename(self.original_file.name))[0]
            self.transcription.save(update_fields=['title'])
            
    def extract_audio_from_video(self):
        """
        Extract audio from video file and save as extracted_audio
        Returns True if successful, False otherwise
        """
        if not self.is_video or not self.original_file:
            return False
            
        try:
            # Create a temporary file for the extracted audio
            with NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_path = temp_audio.name
            
            # Use ffmpeg to extract audio
            cmd = [
                'ffmpeg',
                '-i', self.original_file.path,  # Input file
                '-vn',                         # Disable video
                '-acodec', 'pcm_s16le',        # Audio codec
                '-ar', '16000',                # Sample rate
                '-ac', '1',                    # Mono audio
                '-y',                          # Overwrite output file if it exists
                temp_path                      # Output file
            ]
            
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Save the extracted audio to the model
                with open(temp_path, 'rb') as audio_file:
                    filename = f"{os.path.splitext(os.path.basename(self.original_file.name))[0]}.wav"
                    self.extracted_audio.save(filename, ContentFile(audio_file.read()), save=False)
                
                self.audio_extracted = True
                self.save()
                return True
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Error extracting audio from video: {e}")
                logger.error(f"FFmpeg stderr: {e.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error in extract_audio_from_video: {e}")
            return False
            
        finally:
            # Clean up temporary file if it exists
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error cleaning up temp file {temp_path}: {e}")
    
    def get_audio_file(self):
        """
        Returns the appropriate audio file for processing
        For videos, returns the extracted audio. For audio files, returns the original.
        """
        if self.is_video and self.extracted_audio:
            return self.extracted_audio
        return self.original_file
    
    def delete(self, *args, **kwargs):
        """Delete associated files when the model is deleted"""
        # Delete original file
        if self.original_file:
            storage, path = self.original_file.storage, self.original_file.path
            if storage.exists(path):
                storage.delete(path)
        
        # Delete extracted audio if it exists
        if self.extracted_audio:
            storage, path = self.extracted_audio.storage, self.extracted_audio.path
            if storage.exists(path):
                storage.delete(path)
        
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"Media file for {self.transcription}"

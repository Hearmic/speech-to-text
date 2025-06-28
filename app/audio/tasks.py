import os
import gc
import time
import logging
import subprocess
import tempfile
import shutil
import os.path
import torch
import json
from pathlib import Path
from celery import shared_task, chain
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone

# Import diarization module
try:
    from .diarization import SpeakerDiarizer, merge_transcription_with_diarization
    DIARIZATION_AVAILABLE = True
except ImportError as e:
    logger = get_task_logger(__name__)
    logger.warning(f"Failed to import diarization module: {e}")
    DIARIZATION_AVAILABLE = False

# Initialize diarizer
diarizer = None
if DIARIZATION_AVAILABLE:
    try:
        diarizer = SpeakerDiarizer()
        if not diarizer.is_available():
            logger.warning("Speaker diarization is not available")
            DIARIZATION_AVAILABLE = False
    except Exception as e:
        logger.error(f"Failed to initialize speaker diarizer: {e}")
        DIARIZATION_AVAILABLE = False

# Make psutil and humanize optional
try:
    from psutil import Process
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil module not available. Memory usage monitoring will be disabled.")

try:
    import humanize
    HUMANIZE_AVAILABLE = True
except ImportError:
    HUMANIZE_AVAILABLE = False
    logger.warning("humanize module not available. Human-readable file sizes will be disabled.")

# Try to import memory profiler for debugging
try:
    from memory_profiler import profile
    HAS_MEMORY_PROFILER = True
except ImportError:
    HAS_MEMORY_PROFILER = False
    def profile(func):
        return func  # No-op decorator if memory_profiler is not installed

# Set Whisper model cache directory from environment variable or use /tmp/whisper-cache
WHISPER_CACHE_DIR = os.environ.get('WHISPER_CACHE_DIR', '/tmp/whisper-cache')
try:
    os.makedirs(WHISPER_CACHE_DIR, exist_ok=True, mode=0o777)
except Exception as e:
    logger.warning(f"Could not create Whisper cache directory: {e}")
    # Fall back to a temporary directory
    WHISPER_CACHE_DIR = tempfile.mkdtemp(prefix='whisper-cache-')
    logger.info(f"Using temporary directory for Whisper cache: {WHISPER_CACHE_DIR}")

# Set up logging
logger = get_task_logger(__name__)

# Import models after setting up logging
# Using local imports within functions to avoid circular imports
# and importing at runtime when needed

# Import whisper after setting up logging to catch any import errors
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import Whisper: {e}")
    WHISPER_AVAILABLE = False

def _load_whisper_model(model_name='base'):
    """Load Whisper model with memory optimizations"""
    if not WHISPER_AVAILABLE:
        raise ImportError("Whisper is not available. Please install it with 'pip install openai-whisper'")
    
    logger.info(f"Loading Whisper model: {model_name}")
    
    # Set environment variables for PyTorch memory management
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    
    # Try to enable memory-efficient attention
    try:
        import xformers.ops
        torch.backends.cuda.enable_flash_sdp(True)
        torch.backends.cuda.enable_mem_efficient_sdp(True)
        logger.info("Enabled memory-efficient attention with xFormers")
    except ImportError:
        logger.info("xFormers not available, using default attention")
    
    try:
        # Load the model with specific optimizations
        model = whisper.load_model(
            model_name,
            download_root=WHISPER_CACHE_DIR,
            device='cuda' if torch.cuda.is_available() else 'cpu',
            in_memory=False  # Don't load the entire model into memory at once
        )
        
        # Set model to eval mode and disable gradients
        model.eval()
        for param in model.parameters():
            param.requires_grad = False
            
        return model
    except Exception as e:
        logger.error(f"Error loading Whisper model {model_name}: {e}")
        # If not base model, try falling back to base
        if model_name != 'base':
            logger.info("Falling back to base model")
            return _load_whisper_model('base')
        raise


def log_memory_usage(prefix=""):
    """Log current memory usage"""
    # Log CPU memory if psutil is available
    if PSUTIL_AVAILABLE:
        try:
            process = Process()
            mem_info = process.memory_info()
            if HUMANIZE_AVAILABLE:
                logger.info(
                    f"{prefix}Memory - RSS: {humanize.naturalsize(mem_info.rss)}, "
                    f"VMS: {humanize.naturalsize(mem_info.vms)}, "
                    f"Shared: {humanize.naturalsize(mem_info.shared)}"
                )
            else:
                logger.info(
                    f"{prefix}Memory - RSS: {mem_info.rss} bytes, "
                    f"VMS: {mem_info.vms} bytes, "
                    f"Shared: {mem_info.shared} bytes"
                )
        except Exception as e:
            logger.warning(f"Error getting CPU memory info: {e}")
    
    # Log GPU memory if available
    if torch.cuda.is_available():
        try:
            if HUMANIZE_AVAILABLE:
                logger.info(
                    f"{prefix}GPU Memory - Allocated: {humanize.naturalsize(torch.cuda.memory_allocated())}, "
                    f"Reserved: {humanize.naturalsize(torch.cuda.memory_reserved())}"
                )
            else:
                logger.info(
                    f"{prefix}GPU Memory - Allocated: {torch.cuda.memory_allocated()} bytes, "
                    f"Reserved: {torch.cuda.memory_reserved()} bytes"
                )
        except Exception as e:
            logger.warning(f"Error getting GPU memory info: {e}")

def clear_memory():
    """Try to free up memory"""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

# Supported audio and video formats
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS.union(VIDEO_EXTENSIONS)

def convert_to_wav(input_path, is_video=False):
    """Convert audio/video file to WAV format using ffmpeg"""
    logger.info(f"Converting {'video' if is_video else 'audio'} file to WAV format: {input_path}")
    output_path = f"{os.path.splitext(input_path)[0]}.wav"
    
    try:
        # For video files, extract audio only
        if is_video:
            cmd = [
                'ffmpeg',
                '-i', input_path,    # Input file
                '-vn',               # Disable video
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '16000',      # 16kHz sample rate
                '-ac', '1',          # Mono audio
                '-y',                # Overwrite output file
                output_path
            ]
        else:
            # For audio files, just convert to WAV
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',       # Mono audio
                '-y',             # Overwrite output file
                output_path
            ]
            
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Successfully converted to {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        error_msg = f"Error converting file: {e.stderr}"
        logger.error(error_msg)
        raise Exception(f"Failed to convert file: {str(e)}")
    except Exception as e:
        error_msg = f"Unexpected error during conversion: {str(e)}"
        logger.error(error_msg)
        raise

@shared_task(
    bind=True,
    max_retries=3,
    name='audio.tasks.extract_audio_task',
    autoretry_for=(Exception,),
    retry_backoff=60,  # Wait 60s before first retry
    retry_backoff_max=300,  # Max 5 minutes between retries
    retry_jitter=True,  # Add jitter to avoid thundering herd
    soft_time_limit=1800,  # 30 minute soft time limit
    time_limit=2100,  # 35 minute hard time limit
    acks_late=True,  # Don't ack until task is complete
    reject_on_worker_lost=True  # Require the worker to acknowledge task loss
)
def extract_audio_task(self, media_file_id):
    """
    Celery task to extract audio from a video file
    """
    logger.info(f"Starting audio extraction for media file ID: {media_file_id}")
    
    try:
        # Import here to avoid circular imports
        from .models import MediaFile, Transcription
        
        # Get the media file
        media_file = MediaFile.objects.get(id=media_file_id)
        
        # Skip if not a video or already processed
        if not media_file.is_video or media_file.audio_extracted:
            logger.info(f"Skipping audio extraction for media file {media_file_id}: not a video or already processed")
            return
        
        # Call the extract_audio_from_video method
        success = media_file.extract_audio_from_video()
        
        if success:
            logger.info(f"Successfully extracted audio from video {media_file_id}")
            # Update transcription status if needed
            transcription = media_file.transcription
            if transcription.status == Transcription.STATUS_PENDING:
                transcription.status = Transcription.STATUS_PROCESSING
                transcription.save(update_fields=['status'])
                
                # Start the actual transcription process
                transcription.process_audio()
        else:
            logger.error(f"Failed to extract audio from video {media_file_id}")
            # Update transcription status to failed
            transcription = media_file.transcription
            transcription.status = Transcription.STATUS_FAILED
            transcription.save(update_fields=['status'])
            
    except MediaFile.DoesNotExist:
        logger.error(f"MediaFile {media_file_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error in extract_audio_task for media file {media_file_id}: {str(e)}", exc_info=True)
        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60 * self.request.retries)


@shared_task(
    bind=True,
    max_retries=3,
    name='audio.tasks.process_audio_task',
    autoretry_for=(Exception,),
    retry_backoff=60,  # Wait 60s before first retry
    retry_backoff_max=300,  # Max 5 minutes between retries
    retry_jitter=True,  # Add jitter to avoid thundering herd
    soft_time_limit=3600,  # 1 hour soft time limit
    time_limit=3900,  # 1 hour 5 minutes hard time limit
    acks_late=True,  # Don't ack until task is complete
    reject_on_worker_lost=True  # Require the worker to acknowledge task loss
)
@profile  # Will be a no-op if memory_profiler is not installed
def process_audio_task(self, transcription_id):
    """
    Celery task to process audio file and extract text using Whisper AI
    """
    logger.info(f"Starting processing for transcription ID: {transcription_id}")
    
    # Import models here to avoid circular imports
    from .models import Transcription
    
    temp_files = []  # To keep track of temporary files for cleanup
    
    try:
        transcription = Transcription.objects.select_related('media_file').get(pk=transcription_id)
        
        # If this is a video, make sure audio has been extracted
        if hasattr(transcription, 'media_file') and transcription.media_file and transcription.media_file.is_video:
            if not transcription.media_file.audio_extracted:
                logger.error(f"Audio not yet extracted from video for transcription {transcription_id}")
                # Try again in 10 seconds
                raise self.retry(countdown=10)
    except Transcription.DoesNotExist:
        logger.error(f"Transcription {transcription_id} not found")
        return
        
    # If this is a video, make sure audio has been extracted
    if hasattr(transcription, 'media_file') and transcription.media_file and transcription.media_file.is_video:
        if not transcription.media_file.audio_extracted:
            logger.error(f"Audio not yet extracted from video for transcription {transcription_id}")
            # Try again in 10 seconds
            raise self.retry(countdown=10)
        # Update status to processing
        transcription.status = Transcription.STATUS_PROCESSING
        transcription.save(update_fields=['status'])
        
        # Get the associated media file (audio or video)
        try:
            audio_file = transcription.audio_file
            logger.info(f"Found media file: {audio_file.file.name}")
        except AudioFile.DoesNotExist:
            error_msg = f"No media file found for transcription {transcription.id}"
            logger.error(error_msg)
            transcription.status = Transcription.STATUS_FAILED
            transcription.save(update_fields=['status'])
            return {"status": "error", "message": error_msg}
        
        # Get the full path to the media file
        media_path = os.path.join(settings.MEDIA_ROOT, str(audio_file.file))
        logger.info(f"Media file path: {media_path}")
        
        # Check if file exists
        if not os.path.exists(media_path):
            error_msg = f"Media file not found on disk: {media_path}"
            logger.error(error_msg)
            transcription.status = Transcription.STATUS_FAILED
            transcription.save(update_fields=['status'])
            return {"status": "error", "message": error_msg}
            
        # Check file extension
        file_ext = Path(media_path).suffix.lower()
        original_path = media_path
        
        # Check if the file type is supported
        if file_ext not in SUPPORTED_EXTENSIONS:
            error_msg = f"Unsupported file format: {file_ext}. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
            logger.error(error_msg)
            transcription.status = Transcription.STATUS_FAILED
            transcription.save(update_fields=['status'])
            return {"status": "error", "message": error_msg}
        
        # Convert to WAV if needed
        is_video = file_ext in VIDEO_EXTENSIONS
        if file_ext != '.wav':
            logger.info(f"Converting {file_ext} file to WAV format")
            try:
                audio_path = convert_to_wav(media_path, is_video=is_video)
                temp_files.append(audio_path)  # Track for cleanup
                original_path = media_path  # Keep track of original file
            except Exception as e:
                error_msg = f"Failed to convert media file: {str(e)}"
                logger.error(error_msg)
                transcription.status = Transcription.STATUS_FAILED
                transcription.save(update_fields=['status'])
                return {"status": "error", "message": error_msg}
        else:
            audio_path = media_path
        
        log_memory_usage("Before model loading: ")
        
        # Load the Whisper model with memory optimizations
        model_name = transcription.model_used if hasattr(transcription, 'model_used') else 'base'
        logger.info(f"Loading Whisper model: {model_name}")
        model = _load_whisper_model(model_name)
        
        # Update model in use
        transcription.model_used = model_name
        transcription.save(update_fields=['model_used'])
        
        # Log memory usage after loading model
        log_memory_usage("After model loading: ")
        
        # Check if user's subscription includes speaker diarization
        user = transcription.user
        run_diarization = False
        
        if hasattr(user, 'can_use_speaker_diarization') and callable(getattr(user, 'can_use_speaker_diarization')):
            run_diarization = user.can_use_speaker_diarization()
            logger.info(f"Speaker diarization enabled for user {user.id}: {run_diarization}")
        else:
            logger.warning("User model does not have can_use_speaker_diarization method")
        
        # If diarization is not available, log a warning
        if run_diarization and not DIARIZATION_AVAILABLE:
            logger.warning("Speaker diarization is not available. Check if pyannote.audio is installed and configured.")
            run_diarization = False
            
        transcription.has_speaker_diarization = run_diarization
        transcription.save(update_fields=['has_speaker_diarization'])
        
        try:
            # Transcribe the audio file
            logger.info(f"Starting transcription of {audio_path}")
            start_time = time.time()
            
            try:
                # Get language from transcription or auto-detect if not specified
                language = getattr(transcription, 'language', None)
                
                # Prepare transcription options
                transcribe_options = {
                    'fp16': False,  # fp16=False for CPU
                    'task': 'transcribe',
                    'temperature': 0.2,
                    'best_of': 3,
                    'beam_size': 5,
                    'patience': 1.0,
                    'length_penalty': 1.0,
                    'condition_on_previous_text': True,
                    'word_timestamps': True,
                    'suppress_tokens': [-1],
                    'initial_prompt': None
                }
                
                # Only set language if it's specified
                if language and language != 'auto':
                    transcribe_options['language'] = language
                    logger.info(f"Transcribing with language: {language}")
                else:
                    logger.info("Auto-detecting language")
                
                # Transcribe the audio
                model_name = getattr(model, 'name', 'unknown')
                logger.info(f"Starting transcription with model: {model_name}")
                result = model.transcribe(audio_path, **transcribe_options)
                processing_time = time.time() - start_time
                logger.info(f"Transcription completed in {processing_time:.2f} seconds")
                
                transcription.text = result["text"]
                transcription.language = result["language"]
                transcription.duration = result["duration"]
                transcription.word_count = len(result["text"].split())
                
                # Prepare segments
                segments = [
                    {
                        "start": segment["start"],
                        "end": segment["end"],
                        "text": segment["text"].strip(),
                    }
                    for segment in result["segments"]
                ]
                
                # Run speaker diarization if enabled
                if run_diarization and diarizer and diarizer.is_available():
                    try:
                        logger.info("Running speaker diarization...")
                        diarization_result = diarizer.process_audio_file(audio_path)
                        
                        if diarization_result:
                            # Merge transcription with diarization
                            merged_segments = merge_transcription_with_diarization(
                                segments, 
                                diarization_result.segments
                            )
                            
                            # Update segments with speaker information
                            segments = merged_segments
                            
                            # Save speaker information
                            transcription.speakers = diarization_result.speakers
                            transcription.speaker_segments = diarization_result.segments
                            
                            logger.info(f"Identified {len(diarization_result.speakers)} speakers")
                        else:
                            logger.warning("Speaker diarization returned no results")
                            
                    except Exception as e:
                        logger.error(f"Error during speaker diarization: {e}", exc_info=True)
                        # Continue with transcription even if diarization fails
                
                # Save segments to transcription
                transcription.segments = segments
                
                # Update status and save
                transcription.status = Transcription.STATUS_COMPLETED
                transcription.processing_time = time.time() - start_time
                transcription.save()
                
                logger.info(f"Successfully processed transcription {transcription.id}")
                logger.info(f"Processing time: {transcription.processing_time:.2f} seconds")
                
                # Update the audio file duration if we have segments
                if segments:
                    # Get duration from the last segment's end time
                    audio_file.duration = segments[-1]["end"]
                else:
                    # Fallback: Try to get duration using ffprobe
                    try:
                        import subprocess
                        # Ensure path is converted to string for ffprobe
                        audio_path_str = str(audio_path)
                        cmd = [
                            'ffprobe',
                            '-v', 'error',
                            '-show_entries', 'format=duration',
                            '-of', 'default=noprint_wrappers=1:nokey=1',
                            audio_path_str
                        ]
                        duration = float(subprocess.check_output(cmd).decode('utf-8').strip())
                        audio_file.duration = duration
                    except Exception as e:
                        logger.warning(f"Could not determine audio duration: {str(e)}")
                        audio_file.duration = 0  # Default to 0 if duration cannot be determined
                
                # Only update the duration field, not updated_at
                audio_file.save(update_fields=['duration'])
                
                return {
                    "status": "success",
                    "transcription_id": str(transcription.id),
                    "processing_time": processing_time,
                    "is_video": is_video
                }
                
            except Exception as e:
                error_msg = f"Error during transcription: {str(e)}"
                logger.error(error_msg, exc_info=True)
                transcription.status = Transcription.STATUS_FAILED
                transcription.save(update_fields=['status'])
                # Re-raise the exception to trigger retry
                raise self.retry(exc=e, countdown=60)
                
        except Exception as e:
            # Import here to avoid circular imports
            from django.db import transaction
            from django.core.exceptions import ObjectDoesNotExist
            
            # Handle the case where the transcription doesn't exist
            if isinstance(e, ObjectDoesNotExist) or "does not exist" in str(e).lower():
                logger.error(f"Transcription with id {transcription_id} does not exist")
                return {"status": "error", "message": f"Transcription with id {transcription_id} does not exist"}
            
            # Log the full error for debugging
            error_message = str(e)[:500]  # Limit error message length
            logger.error(f"Error in process_audio_task for transcription {transcription_id}: {error_message}", exc_info=True)
            
            # Update status to failed if we can, using transaction for safety
            try:
                from .models import Transcription
                with transaction.atomic():
                    try:
                        transcription = Transcription.objects.get(id=transcription_id)
                        transcription.status = 'failed'  # Use string literal to avoid dependency
                        transcription.text = f"Unexpected error: {error_message}"
                        transcription.save(update_fields=['status', 'text'])
                    except Exception as save_error:
                        logger.error(f"Failed to update transcription status: {str(save_error)}")
                        # If we can't update the status, we should still handle the retry logic
            except ImportError as ie:
                logger.error(f"Failed to import Transcription model: {str(ie)}")
            
            # Retry the task with exponential backoff, but not for certain errors
            if isinstance(e, (ValueError, TypeError, AttributeError, ImportError)):
                # Don't retry for programming errors
                logger.error(f"Not retrying due to programming error: {str(e)}")
                raise
                
            countdown = 60 * (2 ** (self.request.retries - 1))  # 1st retry: 60s, 2nd: 120s, 3rd: 240s
            max_retry_delay = min(countdown, 300)  # Max 5 minutes delay
            logger.warning(f"Retrying task in {max_retry_delay} seconds (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=max_retry_delay)                 
            
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        if os.path.isdir(temp_file):
                            shutil.rmtree(temp_file)
                        else:
                            os.remove(temp_file)
                        logger.info(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Could not clean up temporary file {temp_file}: {str(e)}")
            
            # Clean up temporary WAV file if created
            if os.path.exists(audio_path) and audio_path != media_path:
                try:
                    os.remove(audio_path)
                    logger.info(f"Cleaned up temporary file: {audio_path}")
                except Exception as e:
                    logger.warning(f"Error cleaning up temporary file {audio_path}: {e}")
            
            # Explicitly clean up model and free memory
            if 'model' in locals():
                del model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                gc.collect()
                log_memory_usage("After cleanup: ")
        

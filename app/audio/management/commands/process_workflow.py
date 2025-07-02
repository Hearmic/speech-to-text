from django.core.management.base import BaseCommand
from audio.models import MediaFile, Transcription
from audio.tasks import extract_audio_task, process_audio_task

class Command(BaseCommand):
    help = 'Process pending media files and transcriptions'

    def handle(self, *args, **options):
        # Process media files that haven't been extracted yet
        pending_media = MediaFile.objects.filter(audio_extracted=False, is_video=True)
        self.stdout.write(f'Found {pending_media.count()} media files to process')
        
        for media in pending_media:
            self.stdout.write(f'Extracting audio from media {media.id}...')
            try:
                extract_audio_task(media.id)
                self.stdout.write(self.style.SUCCESS(f'Successfully extracted audio from {media.id}'))
            except Exception as e:
                self.stderr.write(f'Error extracting audio from {media.id}: {str(e)}')
        
        # Now process pending transcriptions
        pending_transcriptions = Transcription.objects.filter(status='pending')
        self.stdout.write(f'Found {pending_transcriptions.count()} pending transcriptions')
        
        for transcription in pending_transcriptions:
            self.stdout.write(f'Processing transcription {transcription.id}...')
            try:
                process_audio_task(transcription.id)
                self.stdout.write(self.style.SUCCESS(f'Successfully processed transcription {transcription.id}'))
            except Exception as e:
                self.stderr.write(f'Error processing transcription {transcription.id}: {str(e)}')

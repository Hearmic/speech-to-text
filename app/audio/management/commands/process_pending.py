from django.core.management.base import BaseCommand
from audio.models import Transcription
from audio.tasks import process_audio_task

class Command(BaseCommand):
    help = 'Process pending transcriptions'

    def handle(self, *args, **options):
        # Get all pending transcriptions
        pending = Transcription.objects.filter(status='pending')
        self.stdout.write(f'Found {pending.count()} pending transcriptions')
        
        # Process each pending transcription
        for transcription in pending:
            self.stdout.write(f'Processing transcription {transcription.id}...')
            try:
                # Call the task directly (synchronously for debugging)
                process_audio_task(transcription.id)
                self.stdout.write(self.style.SUCCESS(f'Successfully processed {transcription.id}'))
            except Exception as e:
                self.stderr.write(f'Error processing {transcription.id}: {str(e)}')

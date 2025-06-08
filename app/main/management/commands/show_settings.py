from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Show current Django settings'

    def handle(self, *args, **options):
        self.stdout.write("=== Current Settings ===")
        self.stdout.write(f"DEBUG: {settings.DEBUG}")
        self.stdout.write(f"INSTALLED_APPS: {settings.INSTALLED_APPS}")
        self.stdout.write(f"MIDDLEWARE: {settings.MIDDLEWARE}")

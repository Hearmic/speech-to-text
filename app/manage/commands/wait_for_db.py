import os
import time
import sys
import psycopg2
from django.core.management.base import BaseCommand


def wait_for_db():
    """Wait for PostgreSQL to be available"""
    max_retries = 30
    retry_delay = 2  # seconds
    
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME', 'speech2text'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres'),
                host=os.getenv('DB_HOST', 'db'),
                port=os.getenv('DB_PORT', '5432')
            )
            conn.close()
            print('Database is available')
            return True
        except Exception as e:
            print(f'Waiting for database... (Attempt {i + 1}/{max_retries})')
            if i == max_retries - 1:
                print('Max retries reached. Database is not available.')
                return False
            time.sleep(retry_delay)


class Command(BaseCommand):
    help = 'Waits for the database to be available before proceeding.'

    def handle(self, *args, **options):
        if not wait_for_db():
            sys.exit(1)

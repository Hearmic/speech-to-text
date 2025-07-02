import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set the default Django settings module for the 'celery' program.
# Use the full path to the base settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings.base')

# Import Celery after setting the correct Python path
from celery import Celery, signals
from celery.concurrency import asynpool

# Configure asyncio to use the 'uvloop' event loop if available
try:
    import uvloop
    import asyncio
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

# Create Celery app
app = Celery('app.app')

# Configure Redis connection settings
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 100
app.conf.broker_transport_options = {
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 0.5,
}

# Configure result backend settings
app.conf.result_backend = 'django-db'
app.conf.result_extended = True

# Task configuration
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_max_tasks_per_child = 100
app.conf.task_default_priority = 5
app.conf.task_queue_max_priority = 10

# Timeouts
app.conf.broker_transport_options = {
    'visibility_timeout': 43200,  # 12 hours
    'fanout_prefix': True,
    'fanout_patterns': True,
    'socket_connect_timeout': 5,
    'socket_keepalive': True,
    'socket_timeout': 5,
}

# Beat configuration if using scheduled tasks
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.result_backend = None

# Optimization: Disable task events if not needed
app.conf.worker_send_task_events = False
app.conf.task_send_sent_event = False

# Configure task timeouts
app.conf.task_time_limit = 3600  # 1 hour
app.conf.task_soft_time_limit = 3600  # 1 hour

# Optimize memory usage
app.conf.worker_max_tasks_per_child = 10
app.conf.worker_max_memory_per_child = 300000  # 300MB

# Disable prefetching to prevent memory issues with large models
app.conf.worker_prefetch_multiplier = 1

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(['audio'])

# This will make sure the tasks are imported when Django starts
# but only when the Celery worker starts, not during Django's initialization
if 'worker' in sys.argv[0]:
    from django.apps import apps
    apps.check_apps_ready()
    
    # Explicitly import tasks to ensure they're registered
    from audio import tasks  # noqa
    
    # Print registered tasks for debugging
    print("Registered tasks:", list(app.tasks.keys()))


@signals.worker_process_init.connect
def setup_worker_process(**kwargs):
    """Initialize worker process."""
    # Set up process-specific settings
    import os
    import torch
    
    # Reduce PyTorch memory fragmentation
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    
    # Enable memory-efficient attention if available
    try:
        from xformers.ops import memory_efficient_attention
        torch.backends.cuda.enable_flash_sdp(True)
        torch.backends.cuda.enable_mem_efficient_sdp(True)
    except ImportError:
        pass


@signals.task_prerun.connect
def before_task_run(task_id, task, *args, **kwargs):
    """Run before each task."""
    # Clear CUDA cache before each task to prevent OOM
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


@signals.task_postrun.connect
def after_task_run(task_id, task, *args, **kwargs):
    """Run after each task."""
    # Clear CUDA cache after each task to free memory
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass

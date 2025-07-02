# This is an empty file to make Python treat the directory as a package
# We're not importing views here to avoid circular imports

# Define __all__ to specify what should be available when importing the package
__all__ = [
    'audio_list',
    'audio_detail',
    'delete_audio',
    'upload_audio',
    'check_audio_status',
    'check_model_availability'
]

# Lazy imports
def __getattr__(name):
    if name in __all__:
        # Import the views module only when needed
        from . import views
        return getattr(views, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
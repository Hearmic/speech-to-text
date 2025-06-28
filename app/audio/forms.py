from django import forms
from django.conf import settings
from .models import Transcription

# Import the subscription models
try:
    from subscriptions.models import SubscriptionPlan
except ImportError:
    SubscriptionPlan = None

class AudioUploadForm(forms.ModelForm):
    audio_file = forms.FileField(
        label='Audio File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'audio/*,video/*',
            'required': True
        })
    )
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('it', 'Italian'),
        ('pt', 'Portuguese'),
        ('ru', 'Russian'),
        ('ja', 'Japanese'),
        ('zh', 'Chinese'),
        ('hi', 'Hindi'),
    ]
    
    language = forms.ChoiceField(
        label='Language',
        choices=LANGUAGE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='en'
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Default available models for non-authenticated users or users without subscription
        available_models = ['tiny', 'base']
        max_model = 'base'
        
        # For debugging
        print(f"Initializing form for user: {self.user}")
        
        # Check if user is a superuser
        if self.user and self.user.is_authenticated and self.user.is_superuser:
            print(f"Superuser detected: {self.user}")
            # Grant access to all models for superusers
            available_models = ['tiny', 'base', 'small', 'medium', 'large']
            max_model = 'large'
        elif self.user and self.user.is_authenticated:
            print(f"User is authenticated: {self.user}")
            # Check if user has a subscription with the correct attributes
            if hasattr(self.user, 'subscription') and self.user.subscription and hasattr(self.user.subscription, 'plan'):
                try:
                    # Get available models based on subscription
                    subscription = self.user.subscription.plan
                    available_models = getattr(subscription, 'available_models', ['tiny', 'base'])
                    max_model = getattr(subscription, 'max_model_size', 'base')
                    print(f"Subscription found. Available models: {available_models}, Max model: {max_model}")
                except Exception as e:
                    print(f"Error getting subscription: {e}")
                    # Fall back to free tier on error
                    available_models = ['tiny', 'base']
                    max_model = 'base'
            else:
                print("User has no valid subscription, using free tier models")
                available_models = ['tiny', 'base']
                max_model = 'base'
        else:
            print("User is not authenticated, using free tier models")
            available_models = ['tiny', 'base']
            max_model = 'base'
        
        # Create model choices with all models, but mark unavailable ones
        all_models = [
            ('tiny', 'Tiny (Fastest, lowest accuracy)'),
            ('base', 'Base (Faster, lower accuracy)'),
            ('small', 'Small (Good balance)'),
            ('medium', 'Medium (Better accuracy)'),
            ('large', 'Large (Best accuracy, slowest)')
        ]
        
        model_choices = []
        for model_id, model_name in all_models:
            if model_id in available_models:
                model_choices.append((model_id, model_name))
            else:
                # Show upgrade message for unavailable models
                model_choices.append((
                    model_id,
                    f"{model_name} (Upgrade required)"
                ))
        
        # Debug output
        print(f"Available models: {available_models}")
        print(f"Model choices: {model_choices}")
        
        # Add model field
        self.fields['model'] = forms.ChoiceField(
            label='Transcription Model',
            choices=model_choices,
            initial=max_model if max_model in available_models else 'base',
            widget=forms.Select(attrs={
                'class': 'form-select',
                'id': 'model-select',  # Add ID for easier selection
                'hx-get': '/check-model-availability/',
                'hx-trigger': 'change',
                'hx-target': '#model-warning',
                'hx-swap': 'innerHTML',
                'onchange': 'checkModelAvailability()'  # Ensure this fires on change
            }),
            help_text='Choose between speed and accuracy. Larger models are more accurate but slower.'
        )
        
        # Debug the form fields
        print(f"Form fields: {self.fields.keys()}")
    
    class Meta:
        model = Transcription
        fields = ['title', 'language']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a title for this transcription'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        if 'model' not in cleaned_data:
            return cleaned_data
            
        selected_model = cleaned_data['model']
        
        # Superusers can use any model
        if self.user and self.user.is_authenticated and self.user.is_superuser:
            return cleaned_data
            
        # Get available models based on subscription for regular users
        available_models = ['tiny', 'base']  # Default for non-authenticated users
        if self.user and self.user.is_authenticated and hasattr(self.user, 'subscription'):
            try:
                available_models = self.user.subscription.plan.available_models
            except Exception as e:
                print(f"Error getting available models: {e}")
        
        # Check if selected model is available
        if selected_model not in available_models:
            self.add_error('model', 'The selected model is not available with your current subscription.')
        
        return cleaned_data
    
    def save(self, commit=True):
        transcription = super().save(commit=False)
        if hasattr(self, 'cleaned_data') and 'model' in self.cleaned_data:
            transcription.model_used = self.cleaned_data['model']
        if commit:
            transcription.save()
        return transcription

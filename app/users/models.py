from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings

# Import the SubscriptionPlan from the subscriptions app
from subscriptions.models import SubscriptionPlan

class User(AbstractUser):
    """Custom user model with subscription support"""
    subscription = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscribers'
    )
    subscription_ends = models.DateTimeField(null=True, blank=True)
    credits = models.IntegerField(default=0)
    is_trial_used = models.BooleanField(default=False)
    
    def has_active_subscription(self):
        """Check if the user has an active subscription"""
        if self.subscription_ends and self.subscription_ends > timezone.now():
            return True
        return False
    
    def get_priority(self):
        """Get the user's priority in the processing queue"""
        if self.has_active_subscription() and self.subscription:
            return self.subscription.priority
        return 0  # Default priority for free users
        
    def get_remaining_credits(self):
        """Get the user's remaining credits"""
        return self.credits
    
    def can_process_audio(self, audio_length_seconds):
        """Check if the user can process an audio file of the given length"""
        if not self.subscription:
            return False
            
        # Check audio length limit
        max_audio_seconds = self.subscription.max_audio_minutes * 60
        if audio_length_seconds > max_audio_seconds:
            return False
            
        # Check monthly file limit
        from subscriptions.models import UsageRecord
        usage, _ = UsageRecord.get_or_create_current_month(self)
        if usage.has_reached_limit(self.subscription):
            return False
            
        return True
        
    def can_use_speaker_diarization(self):
        """Check if the user's subscription includes speaker diarization feature"""
        if not self.subscription:
            return False
        return self.subscription.speaker_diarization_enabled

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

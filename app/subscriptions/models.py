import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, F, ExpressionWrapper, DurationField, IntegerField
from django.db.models.functions import Now

class SubscriptionPlan(models.Model):
    """Subscription plans that users can subscribe to"""
    # Available Whisper models with their relative sizes and capabilities
    WHISPER_TINY = 'tiny'
    WHISPER_BASE = 'base'
    WHISPER_SMALL = 'small'
    WHISPER_MEDIUM = 'medium'
    WHISPER_LARGE = 'large'
    
    WHISPER_MODEL_CHOICES = [
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
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(
        unique=True,
        help_text='A short label for the plan, used in URLs and references',
        max_length=50
    )
    description = models.TextField(help_text='Detailed description of the plan features')
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    priority = models.IntegerField(
        default=0,
        help_text="Higher number means higher priority in processing queue"
    )
    max_audio_minutes = models.IntegerField(
        default=30,
        help_text="Maximum audio length in minutes per file"
    )
    max_files_per_month = models.IntegerField(
        default=10,
        help_text="Maximum number of files that can be processed per month"
    )
    supported_models = models.JSONField(
        default=list,
        help_text="List of supported Whisper models (tiny, base, small, medium, large)"
    )
    max_model_size = models.CharField(
        max_length=10,
        choices=WHISPER_MODEL_CHOICES,
        default=WHISPER_BASE,
        help_text="Maximum model size allowed for this plan"
    )
    supports_api = models.BooleanField(default=False)
    has_ads = models.BooleanField(default=True)
    can_download = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def available_models(self):
        """Return list of available models for this subscription"""
        all_models = [model[0] for model in self.WHISPER_MODEL_CHOICES]
        max_index = all_models.index(self.max_model_size) + 1
        return all_models[:max_index]
    
    def get_model_display_name(self, model_size):
        """Get display name for a model size"""
        return self.MODEL_DISPLAY_NAMES.get(model_size, model_size.capitalize())
    
    def can_use_model(self, model_size):
        """Check if this plan can use the specified model"""
        return model_size in self.available_models

    class Meta:
        ordering = ['priority']

    def __str__(self):
        return self.name

    def get_features(self):
        """Return a list of features for this plan"""
        features = [
            f"{self.max_audio_minutes} minutes max audio length",
            f"{self.max_files_per_month} files per month",
            "API access" if self.supports_api else "No API access",
            "Ad-free" if not self.has_ads else "Includes ads",
            "Download transcripts" if self.can_download else "No downloads"
        ]
        return features


class UserSubscription(models.Model):
    """Tracks user subscriptions to plans"""
    STATUS_ACTIVE = 'active'
    STATUS_CANCELED = 'canceled'
    STATUS_PAST_DUE = 'past_due'
    STATUS_UNPAID = 'unpaid'
    STATUS_TRIALING = 'trialing'
    STATUS_INCOMPLETE = 'incomplete'
    STATUS_INCOMPLETE_EXPIRED = 'incomplete_expired'
    STATUS_PAUSED = 'paused'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CANCELED, 'Canceled'),
        (STATUS_PAST_DUE, 'Past Due'),
        (STATUS_UNPAID, 'Unpaid'),
        (STATUS_TRIALING, 'Trialing'),
        (STATUS_INCOMPLETE, 'Incomplete'),
        (STATUS_INCOMPLETE_EXPIRED, 'Incomplete Expired'),
        (STATUS_PAUSED, 'Paused'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_subscription'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        related_name='subscriptions'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_INCOMPLETE
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    trial_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.plan.name if self.plan else 'No Plan'}"

    @property
    def is_active(self):
        """Check if the subscription is currently active"""
        now = timezone.now()
        return (
            self.status in [self.STATUS_ACTIVE, self.STATUS_TRIALING] and
            (self.current_period_end is None or self.current_period_end > now) and
            not self.cancel_at_period_end
        )

    @property
    def is_trialing(self):
        """Check if the user is in the trial period"""
        now = timezone.now()
        return (
            self.status == self.STATUS_TRIALING and
            self.trial_end and
            self.trial_end > now
        )

    def get_remaining_trial_days(self):
        """Get remaining trial days"""
        if not self.is_trialing or not self.trial_end:
            return 0
        return (self.trial_end - timezone.now()).days


class UsageRecord(models.Model):
    """Tracks user's monthly usage against their subscription limits"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    files_processed = models.IntegerField(default=0)
    total_audio_seconds = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.user.email} - {self.year}-{self.month:02d}: {self.files_processed} files"

    @classmethod
    def get_or_create_current_month(cls, user):
        """Get or create usage record for the current month"""
        now = timezone.now()
        return cls.objects.get_or_create(
            user=user,
            year=now.year,
            month=now.month
        )

    def has_reached_limit(self, plan):
        """Check if the user has reached their monthly limit"""
        if not plan:
            return True
        return self.files_processed >= plan.max_files_per_month

    def add_usage(self, audio_seconds):
        """Add usage to the current month"""
        self.files_processed = models.F('files_processed') + 1
        self.total_audio_seconds = models.F('total_audio_seconds') + audio_seconds
        self.save(update_fields=['files_processed', 'total_audio_seconds', 'updated_at'])


class PaymentHistory(models.Model):
    """Tracks payment history for subscriptions"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_history'
    )
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(max_length=20)
    stripe_payment_intent_id = models.CharField(max_length=255)
    receipt_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Payment history'

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency.upper()} - {self.status}"

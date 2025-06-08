from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import SubscriptionPlan, UserSubscription
from django.utils import timezone
from datetime import timedelta

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_free_subscription(sender, instance, created, **kwargs):
    """
    Create a free subscription for new users.
    """
    if created:
        # Get or create the free plan
        free_plan, created = SubscriptionPlan.objects.get_or_create(
            slug='free',
            defaults={
                'name': 'Free Plan',
                'description': 'Free plan with basic features',
                'price_monthly': 0,
                'priority': 0,
                'max_audio_minutes': 30,
                'max_files_per_month': 10,
                'max_model_size': 'base',
                'supports_api': False,
                'has_ads': True,
                'can_download': False,
                'is_active': True
            }
        )
        
        # Create the user subscription
        UserSubscription.objects.create(
            user=instance,
            plan=free_plan,
            status=UserSubscription.STATUS_ACTIVE,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=3650),  # 10 years
            trial_end=timezone.now() + timedelta(days=30)  # 30-day trial
        )

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from subscriptions.models import SubscriptionPlan, UserSubscription
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Assigns a free subscription to all users who don\'t have one'

    def handle(self, *args, **options):
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

        if created:
            self.stdout.write(self.style.SUCCESS('Created free subscription plan'))
        else:
            self.stdout.write('Using existing free subscription plan')

        # Get all users without a subscription
        users_without_subscription = User.objects.filter(
            user_subscription__isnull=True
        )

        count = 0
        for user in users_without_subscription:
            # Create the user subscription
            UserSubscription.objects.create(
                user=user,
                plan=free_plan,
                status=UserSubscription.STATUS_ACTIVE,
                current_period_start=timezone.now(),
                current_period_end=timezone.now() + timedelta(days=3650),  # 10 years
                trial_end=timezone.now() + timedelta(days=30)  # 30-day trial
            )
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Assigned free subscription to {count} users')
        )

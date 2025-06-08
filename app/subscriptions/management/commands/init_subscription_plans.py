from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Initialize subscription plans'

    def handle(self, *args, **options):
        # Free Plan
        free_plan, created = SubscriptionPlan.objects.get_or_create(
            name='Free',
            defaults={
                'slug': 'free',
                'description': 'Basic plan with limited features and ads',
                'price_monthly': 0,
                'price_yearly': 0,
                'priority': 1,
                'max_audio_minutes': 30,
                'max_files_per_month': 10,
                'supports_api': False,
                'has_ads': True,
                'can_download': False,
                'is_active': True,
            }
        )
        
        # Pro Plan
        pro_plan, created = SubscriptionPlan.objects.get_or_create(
            name='Pro',
            defaults={
                'slug': 'pro',
                'description': 'Ad-free experience with higher limits',
                'price_monthly': 9.99,
                'price_yearly': 99.99,
                'priority': 2,
                'max_audio_minutes': 120,
                'max_files_per_month': 100,
                'supports_api': True,
                'has_ads': False,
                'can_download': True,
                'is_active': True,
            }
        )
        
        # Premium Plan
        premium_plan, created = SubscriptionPlan.objects.get_or_create(
            name='Premium',
            defaults={
                'slug': 'premium',
                'description': 'Unlimited access with highest priority',
                'price_monthly': 29.99,
                'price_yearly': 299.99,
                'priority': 3,
                'max_audio_minutes': 300,  # 5 hours
                'max_files_per_month': 1000,  # Effectively unlimited for most users
                'supports_api': True,
                'has_ads': False,
                'can_download': True,
                'is_active': True,
            }
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully initialized subscription plans'))

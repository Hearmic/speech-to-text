from django.core.management.base import BaseCommand
from django.conf import settings
from subscriptions.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Set up or update subscription plans with model access levels'

    def handle(self, *args, **options):
        # Define the plans and their model access
        plans = [
            {
                'name': 'Free',
                'slug': 'free',
                'max_model_size': 'base',
                'models': ['tiny', 'base'],
                'price_monthly': 0,
                'max_audio_minutes': 10,
                'max_files_per_month': 5,
            },
            {
                'name': 'Basic',
                'slug': 'basic',
                'max_model_size': 'small',
                'models': ['tiny', 'base', 'small'],
                'price_monthly': 9.99,
                'max_audio_minutes': 30,
                'max_files_per_month': 30,
            },
            {
                'name': 'Pro',
                'slug': 'pro',
                'max_model_size': 'medium',
                'models': ['tiny', 'base', 'small', 'medium'],
                'price_monthly': 29.99,
                'max_audio_minutes': 120,
                'max_files_per_month': 100,
            },
            {
                'name': 'Enterprise',
                'slug': 'enterprise',
                'max_model_size': 'large',
                'models': ['tiny', 'base', 'small', 'medium', 'large'],
                'price_monthly': 99.99,
                'max_audio_minutes': 600,
                'max_files_per_month': 1000,
            },
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                slug=plan_data['slug'],
                defaults={
                    'name': plan_data['name'],
                    'max_model_size': plan_data['max_model_size'],
                    'supported_models': plan_data['models'],
                    'price_monthly': plan_data['price_monthly'],
                    'max_audio_minutes': plan_data['max_audio_minutes'],
                    'max_files_per_month': plan_data['max_files_per_month'],
                    'supports_api': plan_data.get('supports_api', False) or plan_data['slug'] in ['pro', 'enterprise'],
                    'has_ads': plan_data.get('has_ads', True) and plan_data['slug'] == 'free',
                    'can_download': plan_data.get('can_download', True) or plan_data['slug'] != 'free',
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created {plan.name} plan'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated {plan.name} plan'))
        
        self.stdout.write(self.style.SUCCESS('Successfully set up subscription plans'))

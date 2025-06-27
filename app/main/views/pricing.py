from django.shortcuts import render
from django.views import View
from subscriptions.models import SubscriptionPlan

class PricingView(View):
    template_name = 'pricing.html'
    
    def get(self, request, *args, **kwargs):
        # Get active subscription plans
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')
        
        context = {
            'plans': plans,
        }
        return render(request, self.template_name, context)

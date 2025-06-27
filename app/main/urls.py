from django.urls import path
from .views import home, custom_404, ContactView, contact_success, PricingView

app_name = 'main'

urlpatterns = [
    path('', home, name='home'),
    path('pricing/', PricingView.as_view(), name='pricing'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('contact/success/', contact_success, name='contact_success'),
]

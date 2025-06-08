from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from rest_framework.schemas import get_schema_view
from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
# Register your API views here
# router.register(r'example', views.ExampleViewSet)

# Create a schema view for the API
docs_view = get_schema_view(
    title="Speech to Text API",
    description="API documentation for the Speech to Text service",
    version="1.0.0",
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # API root
    path('', views.api_root, name='api-root'),
    
    # Include the router URLs
    path('', include(router.urls)),
    
    # API documentation
    path('schema/', docs_view, name='schema'),
    
    # Authentication endpoints
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
]

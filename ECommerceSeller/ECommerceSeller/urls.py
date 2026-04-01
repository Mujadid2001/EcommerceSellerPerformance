"""
URL configuration for ECommerceSeller project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.db.models import Avg, Count
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.views.static import serve
from django.urls import re_path

def home_view(request):
    """Home page view with system statistics"""
    try:
        from apps.performance.models import Seller, Order, CustomerFeedback
        
        context = {
            'total_sellers': Seller.objects.filter(status='active').count(),
            'total_orders': Order.objects.count(),
            'average_score': round(Seller.objects.aggregate(Avg('performance_score'))['performance_score__avg'] or 0, 1),
            'total_feedback': CustomerFeedback.objects.count(),
        }
    except Exception:
        # If database not ready, provide default values
        context = {
            'total_sellers': 0,
            'total_orders': 0,
            'average_score': 0,
            'total_feedback': 0,
        }
    
    return render(request, 'home.html', context)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin-dashboard/", include("apps.performance.admin_urls")),  # Custom admin interface
    path("", home_view, name="home"),
    path("marketplace/", include("apps.performance.urls")),
    path("auth/", include("apps.authentication.urls")),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema')),
]

if settings.DEBUG:
    # Serve static files (CSS, JS, images) from the static directory
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Also serve from project-level static folder for development
    if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
        for static_dir in settings.STATICFILES_DIRS:
            if str(static_dir) != str(settings.STATIC_ROOT):
                urlpatterns += static(settings.STATIC_URL, document_root=str(static_dir))
    
    # Serve media files
    if hasattr(settings, 'MEDIA_URL') and hasattr(settings, 'MEDIA_ROOT'):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

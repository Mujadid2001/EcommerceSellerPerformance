"""
URL configuration for ECommerceSeller project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

def home_view(request):
    """Simple home page view"""
    return render(request, 'home.html')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin-dashboard/", include("apps.performance.admin_urls")),  # Custom admin interface
    path("", home_view, name="home"),
    path("marketplace/", include("apps.performance.urls")),
    path("auth/", include("apps.authentication.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if hasattr(settings, 'MEDIA_URL'):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

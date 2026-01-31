"""
URLs for authentication endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.authentication.views import AuthenticationViewSet, UserManagementViewSet
from apps.authentication.utils import get_csrf_token

router = DefaultRouter()
router.register(r'authentication', AuthenticationViewSet, basename='auth')
router.register(r'users', UserManagementViewSet, basename='user')

urlpatterns = [
    path('csrf-token/', get_csrf_token, name='csrf-token'),
    path('', include(router.urls)),
]

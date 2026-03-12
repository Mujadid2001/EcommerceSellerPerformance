"""
URLs for authentication endpoints.
"""
from django.urls import path
from apps.authentication.views import AuthenticationViewSet, UserManagementViewSet, login_view, register_view, verify_email_view, logout_view
from apps.authentication.utils import get_csrf_token

urlpatterns = [
    path('csrf-token/', get_csrf_token, name='csrf-token'),
    # Web views
    path('login/', login_view, name='auth-login'),
    path('register/', register_view, name='auth-register'),
    path('verify/', verify_email_view, name='auth-verify'),
    path('logout/', logout_view, name='auth-logout'),
    # API endpoints
    path('api/authentication/register/', AuthenticationViewSet.as_view({'post': 'register'}), name='api-register'),
    path('api/authentication/login/', AuthenticationViewSet.as_view({'post': 'login'}), name='api-login'),
    path('api/authentication/logout/', AuthenticationViewSet.as_view({'post': 'logout'}), name='api-logout'),
    path('api/authentication/verify-email/', AuthenticationViewSet.as_view({'post': 'verify_email'}), name='api-verify-email'),
    path('api/authentication/resend-verification/', AuthenticationViewSet.as_view({'post': 'resend_verification'}), name='api-resend-verification'),
    # User management API endpoints
    path('api/users/', UserManagementViewSet.as_view({'get': 'list'}), name='user-list'),
    path('api/users/<int:pk>/', UserManagementViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='user-detail'),
    path('api/users/me/', UserManagementViewSet.as_view({'get': 'me', 'put': 'update_me'}), name='user-me'),
    path('api/authentication/change-password/', UserManagementViewSet.as_view({'post': 'change_password'}), name='api-change-password'),
    path('api/users/<int:pk>/login-logs/', UserManagementViewSet.as_view({'get': 'login_logs'}), name='user-login-logs'),
]


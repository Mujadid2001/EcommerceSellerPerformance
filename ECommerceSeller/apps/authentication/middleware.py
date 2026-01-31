"""
Authentication and permission middleware for the attendance system.
Handles redirects and access control based on user roles.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from functools import wraps
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated


class AuthenticationMiddleware:
    """Middleware to handle authentication redirects."""

    def __init__(self, get_response):
        self.get_response = get_response
        # Pages that require authentication
        self.protected_pages = [
            '/admin-dashboard/',
            '/teacher-dashboard/',
            '/student-dashboard/',
            '/face-registration/',
            '/attendance-marking/',
        ]

    def __call__(self, request):
        response = self.get_response(request)
        return response


def role_required(*roles):
    """Decorator to check user role."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('home')
            
            user_role = getattr(request.user, 'role', None)
            if user_role not in roles:
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorator to require admin role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'admin':
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def teacher_required(view_func):
    """Decorator to require teacher role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'teacher':
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def student_required(view_func):
    """Decorator to require student role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'student':
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

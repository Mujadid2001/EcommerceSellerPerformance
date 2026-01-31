"""
Permission classes for role-based access control.
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission for admin users only."""
    
    def has_permission(self, request):
        return request.user and request.user.is_authenticated and request.user.is_admin()


class IsUser(permissions.BasePermission):
    """Permission for normal users."""
    
    def has_permission(self, request):
        return request.user and request.user.is_authenticated


"""
Authentication backend for role-based access control.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomAuthenticationBackend(ModelBackend):
    """Custom authentication backend supporting email-based authentication."""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate using email or username.
        """
        try:
            # Try email first
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None
        
        # Check password
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        """Get user by ID."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

"""
Authentication models
"""
import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model with role-based access control."""
    
    class Role(models.TextChoices):
        """User role choices."""
        ADMIN = 'admin', _('Administrator')
        USER = 'user', _('User')
        
    
    # Remove username field
    username = None
    
    # Custom fields
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text=_('Email address must be unique')
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_('Contact phone number')
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
        help_text=_('User role in the system')
    )
    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        help_text=_('User profile picture')
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_('Email verification status')
    )
    is_approved = models.BooleanField(
        default=True,
        help_text=_('Account approved by admin (for teachers)')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(blank=True, null=True)
    
    # Override groups and user_permissions to avoid reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_('The groups this user belongs to.'),
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    
    # Set USERNAME_FIELD
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['password']
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def is_admin(self):
        """Check if user is admin."""
        return self.role == self.Role.ADMIN or self.is_superuser
    
    def is_user(self):
        """Check if user is a regular user."""
        return self.role == self.Role.USER
    
    def get_role_display_verbose(self):
        """Get verbose role display."""
        return dict(self.Role.choices).get(self.role, 'Unknown')


class LoginLog(models.Model):
    """Track user login activities for security auditing."""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_logs'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Reason for failed login attempt')
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Login Log')
        verbose_name_plural = _('Login Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.user.email} - {status} - {self.timestamp}"


class EmailVerificationToken(models.Model):
    """Email verification tokens for user registration."""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='verification_tokens'
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_('Unique verification token')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text=_('Token expiration time')
    )
    is_used = models.BooleanField(
        default=False,
        help_text=_('Whether the token has been used')
    )
    
    class Meta:
        verbose_name = _('Email Verification Token')
        verbose_name_plural = _('Email Verification Tokens')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.token}"
    
    def save(self, *args, **kwargs):
        """Set expiration time on creation."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if token is expired."""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired()

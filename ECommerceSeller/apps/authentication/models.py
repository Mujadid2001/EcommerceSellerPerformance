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
    """Custom user manager for authentication following Django best practices."""
    
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with email verification required."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.USER)
        
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with admin privileges.
        Superusers have is_staff and is_superuser set to True.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model with role-based access control."""
    
    class Role(models.TextChoices):
        """User role choices."""
        ADMIN = 'admin', _('Administrator')
        USER = 'user', _('User')
        SELLER = 'seller', _('Seller')
        
    
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
        help_text=_('Account approved by admin')
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
    
    # Set USERNAME_FIELD and REQUIRED_FIELDS for Django authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Empty because email is USERNAME_FIELD, only prompted for first/last name
    
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
        db_table = 'auth_user'  # Industry standard table name
    
    def __str__(self):
        """String representation showing email and role."""
        full_name = self.get_full_name()
        if full_name:
            return f"{full_name} ({self.email})"
        return self.email
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email
    
    def get_short_name(self):
        """Return the short name for the user (first_name or email)."""
        return self.first_name or self.email.split('@')[0]
    
    def is_admin(self):
        """Check if user has admin privileges."""
        return self.role == self.Role.ADMIN or self.is_superuser or self.is_staff
    
    def is_regular_user(self):
        """Check if user is a regular user (not admin)."""
        return self.role == self.Role.USER and not self.is_superuser and not self.is_staff
    
    def get_role_display_verbose(self):
        """Get verbose role display."""
        if self.is_superuser:
            return 'Super Administrator'
        return dict(self.Role.choices).get(self.role, 'User')
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login_at = timezone.now()
        self.save(update_fields=['last_login_at'])
    
    def send_verification_email(self):
        """Send email verification token to user."""
        from apps.authentication.tasks import send_verification_email_task
        
        # Create verification token
        token = EmailVerificationToken.objects.create(user=self)
        
        # Send email asynchronously
        send_verification_email_task.delay(self.id, str(token.token))
        
        return token


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

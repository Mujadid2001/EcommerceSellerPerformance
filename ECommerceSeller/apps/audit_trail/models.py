"""
Audit Trail models for comprehensive logging of user actions.
Implements FR-11: Audit Logging.
"""
import json
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

User = get_user_model()


class AuditEvent(models.Model):
    """
    Comprehensive audit trail for all system actions.
    Tracks user actions, system changes, and security events.
    """
    
    class EventType(models.TextChoices):
        """Types of auditable events."""
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        REGISTER = 'register', 'Registration'
        PASSWORD_CHANGE = 'password_change', 'Password Change'
        
        # Data operations
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        VIEW = 'view', 'View'
        
        # Report operations
        REPORT_GENERATE = 'report_generate', 'Report Generate'
        REPORT_DOWNLOAD = 'report_download', 'Report Download'
        EXPORT_DATA = 'export_data', 'Data Export'
        IMPORT_DATA = 'import_data', 'Data Import'
        
        # Performance operations
        PERFORMANCE_CALCULATE = 'performance_calculate', 'Performance Calculation'
        SELLER_EVALUATE = 'seller_evaluate', 'Seller Evaluation'
        STATUS_CHANGE = 'status_change', 'Status Change'
        
        # Security events
        FAILED_LOGIN = 'failed_login', 'Failed Login'
        PERMISSION_DENIED = 'permission_denied', 'Permission Denied'
        SUSPICIOUS_ACTIVITY = 'suspicious_activity', 'Suspicious Activity'
    
    class Severity(models.TextChoices):
        """Event severity levels."""
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'
    
    # Event identification
    event_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    
    # Event details
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        db_index=True
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.LOW,
        db_index=True
    )
    
    # User and session info
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events'
    )
    user_email = models.EmailField(null=True, blank=True)  # Store even if user is deleted
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    request_path = models.CharField(max_length=255, null=True, blank=True)
    request_method = models.CharField(max_length=10, null=True, blank=True)
    
    # Event description
    description = models.TextField()
    details = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        help_text="Additional event details in JSON format"
    )
    
    # Related object tracking
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Outcome
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        verbose_name = "Audit Event"
        verbose_name_plural = "Audit Events"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.event_type} by {self.user_email or 'Anonymous'} at {self.timestamp}"
    
    @classmethod
    def log_event(cls, event_type, user=None, description="", **kwargs):
        """
        Convenience method to log audit events.
        
        Args:
            event_type: Type of event from EventType choices
            user: User instance (if applicable)
            description: Human-readable description
            **kwargs: Additional details
        
        Returns:
            AuditEvent: Created audit event instance
        """
        return cls.objects.create(
            event_type=event_type,
            user=user,
            user_email=user.email if user else None,
            description=description,
            details=kwargs
        )


class LoginAttempt(models.Model):
    """
    Specialized model for tracking login attempts.
    Used for security monitoring and brute force detection.
    """
    
    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField(null=True, blank=True)
    
    success = models.BooleanField(default=False, db_index=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        verbose_name = "Login Attempt"
        verbose_name_plural = "Login Attempts"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['email', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{status} login for {self.email} from {self.ip_address}"
    
    @classmethod
    def log_attempt(cls, email, ip_address, success=False, failure_reason=None, user_agent=None):
        """Log a login attempt."""
        return cls.objects.create(
            email=email,
            ip_address=ip_address,
            success=success,
            failure_reason=failure_reason,
            user_agent=user_agent
        )
    
    @classmethod
    def get_failed_attempts(cls, email=None, ip_address=None, hours=1):
        """
        Get failed login attempts for security monitoring.
        
        Args:
            email: Email to filter by
            ip_address: IP to filter by
            hours: Hours back to look
        
        Returns:
            QuerySet: Failed login attempts
        """
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        queryset = cls.objects.filter(
            success=False,
            timestamp__gte=cutoff_time
        )
        
        if email:
            queryset = queryset.filter(email=email)
        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)
        
        return queryset


class DataChangeLog(models.Model):
    """
    Detailed logging of data changes for audit purposes.
    Tracks before/after values for sensitive data modifications.
    """
    
    # Related audit event
    audit_event = models.ForeignKey(
        AuditEvent,
        on_delete=models.CASCADE,
        related_name='data_changes'
    )
    
    # Field details
    field_name = models.CharField(max_length=255)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    
    # Data type information
    field_type = models.CharField(max_length=50, null=True, blank=True)
    
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = "Data Change Log"
        verbose_name_plural = "Data Change Logs"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.field_name}: {self.old_value} → {self.new_value}"


class SystemMetrics(models.Model):
    """
    System performance and usage metrics for monitoring.
    """
    
    metric_name = models.CharField(max_length=100, db_index=True)
    metric_value = models.FloatField()
    unit = models.CharField(max_length=50, null=True, blank=True)
    
    tags = models.JSONField(
        default=dict,
        help_text="Additional metric tags in JSON format"
    )
    
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        verbose_name = "System Metric"
        verbose_name_plural = "System Metrics"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_name', '-timestamp']),
        ]
        unique_together = ['metric_name', 'timestamp']
    
    def __str__(self):
        return f"{self.metric_name}: {self.metric_value} {self.unit or ''}"
    
    @classmethod
    def record_metric(cls, name, value, unit=None, **tags):
        """Record a system metric."""
        return cls.objects.create(
            metric_name=name,
            metric_value=value,
            unit=unit,
            tags=tags
        )
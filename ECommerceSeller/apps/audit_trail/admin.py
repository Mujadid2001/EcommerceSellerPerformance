"""
Admin interface for audit trail models.
Provides comprehensive audit log management for administrators.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import json

from .models import AuditEvent, LoginAttempt, DataChangeLog, SystemMetrics


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """
    Admin interface for audit events.
    Provides comprehensive filtering and search capabilities.
    """
    
    list_display = [
        'event_id_short',
        'event_type',
        'severity_badge',
        'user_email',
        'ip_address',
        'success_badge',
        'timestamp',
        'description_short'
    ]
    
    list_filter = [
        'event_type',
        'severity',
        'success',
        'timestamp',
        ('user', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'user__email',
        'user_email',
        'description',
        'ip_address',
        'request_path',
        'event_id',
    ]
    
    readonly_fields = [
        'event_id',
        'timestamp',
        'user',
        'user_email',
        'session_key',
        'ip_address',
        'user_agent',
        'request_path',
        'request_method',
        'content_type',
        'object_id',
        'formatted_details'
    ]
    
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('event_id', 'event_type', 'severity', 'timestamp', 'success')
        }),
        ('User Information', {
            'fields': ('user', 'user_email', 'session_key')
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent', 'request_path', 'request_method')
        }),
        ('Event Details', {
            'fields': ('description', 'formatted_details', 'error_message')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
    )
    
    def event_id_short(self, obj):
        """Display shortened event ID."""
        return str(obj.event_id)[:8] + '...'
    event_id_short.short_description = 'Event ID'
    
    def severity_badge(self, obj):
        """Display severity with color coding."""
        colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545'
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'
    
    def success_badge(self, obj):
        """Display success status with color coding."""
        if obj.success:
            return format_html(
                '<span style="color: #28a745;">✓ Success</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545;">✗ Failed</span>'
            )
    success_badge.short_description = 'Status'
    
    def description_short(self, obj):
        """Display shortened description."""
        return obj.description[:100] + ('...' if len(obj.description) > 100 else '')
    description_short.short_description = 'Description'
    
    def formatted_details(self, obj):
        """Display formatted JSON details."""
        if obj.details:
            try:
                formatted = json.dumps(obj.details, indent=2)
                return format_html('<pre>{}</pre>', formatted)
            except:
                return str(obj.details)
        return 'No details'
    formatted_details.short_description = 'Details'
    
    def has_add_permission(self, request):
        """Prevent manual addition of audit events."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit events."""
        return False


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """
    Admin interface for login attempts.
    Provides security monitoring capabilities.
    """
    
    list_display = [
        'email',
        'ip_address',
        'success_badge',
        'failure_reason',
        'timestamp',
        'user_agent_short'
    ]
    
    list_filter = [
        'success',
        'timestamp',
    ]
    
    search_fields = [
        'email',
        'ip_address',
        'failure_reason',
    ]
    
    readonly_fields = [
        'email',
        'ip_address',
        'user_agent',
        'success',
        'failure_reason',
        'timestamp'
    ]
    
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def success_badge(self, obj):
        """Display success status with color coding."""
        if obj.success:
            return format_html(
                '<span style="color: #28a745;">✓ Success</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545;">✗ Failed</span>'
            )
    success_badge.short_description = 'Status'
    
    def user_agent_short(self, obj):
        """Display shortened user agent."""
        if obj.user_agent:
            return obj.user_agent[:50] + ('...' if len(obj.user_agent) > 50 else '')
        return 'Unknown'
    user_agent_short.short_description = 'User Agent'
    
    def has_add_permission(self, request):
        """Prevent manual addition of login attempts."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of login attempts."""
        return False


@admin.register(DataChangeLog)
class DataChangeLogAdmin(admin.ModelAdmin):
    """
    Admin interface for data change logs.
    """
    
    list_display = [
        'audit_event',
        'field_name',
        'field_type',
        'old_value_short',
        'new_value_short',
        'timestamp'
    ]
    
    list_filter = [
        'field_name',
        'field_type',
        'timestamp',
    ]
    
    search_fields = [
        'field_name',
        'old_value',
        'new_value',
    ]
    
    readonly_fields = [
        'audit_event',
        'field_name',
        'old_value',
        'new_value',
        'field_type',
        'timestamp'
    ]
    
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def old_value_short(self, obj):
        """Display shortened old value."""
        if obj.old_value:
            return obj.old_value[:50] + ('...' if len(obj.old_value) > 50 else '')
        return 'None'
    old_value_short.short_description = 'Old Value'
    
    def new_value_short(self, obj):
        """Display shortened new value."""
        if obj.new_value:
            return obj.new_value[:50] + ('...' if len(obj.new_value) > 50 else '')
        return 'None'
    new_value_short.short_description = 'New Value'
    
    def has_add_permission(self, request):
        """Prevent manual addition of change logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of change logs."""
        return False


@admin.register(SystemMetrics)
class SystemMetricsAdmin(admin.ModelAdmin):
    """
    Admin interface for system metrics.
    """
    
    list_display = [
        'metric_name',
        'metric_value',
        'unit',
        'timestamp',
        'formatted_tags'
    ]
    
    list_filter = [
        'metric_name',
        'timestamp',
    ]
    
    search_fields = [
        'metric_name',
    ]
    
    readonly_fields = [
        'metric_name',
        'metric_value',
        'unit',
        'tags',
        'timestamp'
    ]
    
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def formatted_tags(self, obj):
        """Display formatted tags."""
        if obj.tags:
            return ', '.join([f"{k}: {v}" for k, v in obj.tags.items()])
        return 'No tags'
    formatted_tags.short_description = 'Tags'
    
    def has_add_permission(self, request):
        """Prevent manual addition of metrics."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of metrics."""
        return False


# Custom admin site configuration
admin.site.site_header = "E-Commerce Seller Performance Admin"
admin.site.site_title = "Seller Performance Admin"
admin.site.index_title = "Administration Dashboard"
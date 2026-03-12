"""
Authentication and permission middleware for the seller performance system.
Handles redirects and access control based on user roles.
Includes comprehensive audit trail logging for FR-11.
"""
import json
import logging
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from functools import wraps
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger('audit')


class AuthenticationMiddleware:
    """Middleware to handle authentication redirects."""

    def __init__(self, get_response):
        self.get_response = get_response
        # Pages that require authentication
        self.protected_pages = [
            '/dashboard/',
            '/admin/',
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
                return redirect('performance:marketplace')
            
            user_role = getattr(request.user, 'role', None)
            if user_role not in roles:
                return redirect('performance:marketplace')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorator to require admin role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'admin':
            return redirect('performance:marketplace')
        return view_func(request, *args, **kwargs)
    return wrapper


def user_required(view_func):
    """Decorator to require authenticated user."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('performance:marketplace')
        return view_func(request, *args, **kwargs)
    return wrapper


class AuditTrailMiddleware(MiddlewareMixin):
    """
    Middleware to automatically log user actions for audit trails.
    Implements FR-11: Audit Logging requirements.
    """
    
    def process_request(self, request):
        """Process incoming requests."""
        # Store request data for later use
        request._audit_data = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'path': request.path,
            'method': request.method,
            'timestamp': None,
        }
        
        return None
    
    def process_response(self, request, response):
        """Process responses and log significant events."""
        
        # Skip logging for static files and health checks
        if self.should_skip_logging(request):
            return response
        
        # Log based on response status and URL patterns
        if hasattr(request, '_audit_data'):
            audit_data = request._audit_data
            
            # Log different events based on URL patterns
            try:
                self.log_request_event(request, response, audit_data)
            except Exception as e:
                # Don't let audit logging break the application
                logger.error(f"Audit logging error: {e}")
        
        return response
    
    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def should_skip_logging(self, request):
        """Determine if request should be skipped from logging."""
        skip_paths = [
            '/static/',
            '/media/',
            '/favicon.ico',
            '/health/',
            '/ping/',
        ]
        
        return any(request.path.startswith(path) for path in skip_paths)
    
    def log_request_event(self, request, response, audit_data):
        """Log request events based on URL patterns."""
        # Import here to avoid circular imports
        from apps.audit_trail.models import AuditEvent, LoginAttempt
        
        path = request.path
        method = request.method
        user = request.user if request.user.is_authenticated else None
        
        # Determine event type based on URL patterns
        event_type = None
        description = ""
        severity = AuditEvent.Severity.LOW
        details = {
            'status_code': response.status_code,
            'content_type': response.get('Content-Type', ''),
        }
        
        # Authentication events
        if '/auth/login' in path:
            if response.status_code == 200:
                event_type = AuditEvent.EventType.LOGIN
                description = f"User login successful: {user.email if user else 'Unknown'}"
                severity = AuditEvent.Severity.MEDIUM
            else:
                event_type = AuditEvent.EventType.FAILED_LOGIN
                description = f"Login attempt failed from {audit_data['ip_address']}"
                severity = AuditEvent.Severity.HIGH
        
        # Report and export events
        elif '/reports/' in path or '/export/' in path:
            if method == 'GET' and 'download' in path:
                event_type = AuditEvent.EventType.REPORT_DOWNLOAD
                description = f"Report downloaded: {path}"
                severity = AuditEvent.Severity.MEDIUM
            elif method == 'POST':
                event_type = AuditEvent.EventType.REPORT_GENERATE
                description = f"Report generated: {path}"
                severity = AuditEvent.Severity.MEDIUM
        
        # Data import/export
        elif '/import/' in path and method == 'POST':
            event_type = AuditEvent.EventType.IMPORT_DATA
            description = f"Data import attempted: {path}"
            severity = AuditEvent.Severity.HIGH
        
        # Performance evaluation events
        elif '/api/sellers/' in path and '/recalculate' in path:
            event_type = AuditEvent.EventType.PERFORMANCE_CALCULATE
            description = f"Performance recalculation triggered"
            severity = AuditEvent.Severity.MEDIUM
        
        # Admin panel access
        elif '/admin/' in path:
            event_type = AuditEvent.EventType.VIEW
            description = f"Admin panel access: {path}"
            severity = AuditEvent.Severity.HIGH if user and user.is_superuser else AuditEvent.Severity.MEDIUM
        
        # Security events
        if response.status_code == 403:
            event_type = AuditEvent.EventType.PERMISSION_DENIED
            description = f"Access denied to {path}"
            severity = AuditEvent.Severity.HIGH
        elif response.status_code >= 500:
            event_type = AuditEvent.EventType.SUSPICIOUS_ACTIVITY
            description = f"Server error on {path}"
            severity = AuditEvent.Severity.HIGH
        
        # Log the event if we identified it
        if event_type:
            try:
                AuditEvent.objects.create(
                    event_type=event_type,
                    severity=severity,
                    user=user,
                    user_email=user.email if user else None,
                    session_key=request.session.session_key,
                    ip_address=audit_data['ip_address'],
                    user_agent=audit_data['user_agent'],
                    request_path=audit_data['path'],
                    request_method=audit_data['method'],
                    description=description,
                    details=details,
                    success=200 <= response.status_code < 400
                )
                
                # Also log to file
                logger.info(
                    f"AUDIT: {event_type} | User: {user.email if user else 'Anonymous'} | "
                    f"IP: {audit_data['ip_address']} | Path: {path} | Status: {response.status_code}"
                )
            
            except Exception as e:
                logger.error(f"Failed to create audit event: {e}")

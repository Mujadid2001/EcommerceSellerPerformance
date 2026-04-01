"""
Request ID middleware for tracing requests across logs and responses.

Adds a unique ID to each request for tracking and debugging purposes.
"""
import uuid
import logging
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

logger = logging.getLogger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Adds a unique request ID to each request for tracing and debugging.
    Also adds timing information to track request performance.
    """
    
    REQUEST_ID_HEADER = 'X-Request-ID'
    REQUEST_ID_ATTR = '_request_id'
    START_TIME_ATTR = '_start_time'
    
    def process_request(self, request):
        """Add request ID and start time to request object."""
        # Use existing header or generate new ID
        request_id = request.META.get('HTTP_X_REQUEST_ID')
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store on request object
        setattr(request, self.REQUEST_ID_ATTR, request_id)
        setattr(request, self.START_TIME_ATTR, timezone.now())
        
        # Add to logging context
        request.META['request_id'] = request_id
        
        return None
    
    def process_response(self, request, response):
        """Add request ID header to response and log timing."""
        request_id = getattr(request, self.REQUEST_ID_ATTR, None)
        
        if request_id:
            # Add to response headers
            response[self.REQUEST_ID_HEADER] = request_id
            
            # Calculate request duration
            start_time = getattr(request, self.START_TIME_ATTR, None)
            if start_time:
                duration = (timezone.now() - start_time).total_seconds() * 1000  # Convert to ms
                response['X-Process-Time'] = f"{duration:.2f}ms"
                
                # Log slow requests
                if duration > 1000:  # 1 second
                    logger.warning(
                        f"SLOW REQUEST: {request.method} {request.path} "
                        f"took {duration:.2f}ms (ID: {request_id})"
                    )
        
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Adds security headers to all responses for hardened API protection.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        
        # Content Security Policy - Allow CDN resources for development
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "https://code.jquery.com "
                "https://cdn.jsdelivr.net "
                "https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' "
                "https://cdn.jsdelivr.net "
                "https://cdnjs.cloudflare.com; "
            "style-src-elem 'self' 'unsafe-inline' "
                "https://cdn.jsdelivr.net "
                "https://cdnjs.cloudflare.com; "
            "font-src 'self' data: "
                "https://cdn.jsdelivr.net "
                "https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:"
        )
        
        # Prevent browsers from MIME-type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Clickjacking protection
        response['X-Frame-Options'] = 'DENY'
        
        # Referrer policy for privacy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Feature policy / Permissions policy
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=()'
        )
        
        return response

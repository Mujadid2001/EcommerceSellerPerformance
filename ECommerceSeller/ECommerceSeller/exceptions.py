"""
Commercial-grade exception handling for ECommerceSeller project.

Following industrial standards:
- Consistent JSON response structure
- Proper HTTP status codes
- Comprehensive logging
- Security-conscious error messages (no sensitive info in production)
"""
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied, NotFound
from rest_framework.response import Response

logger = logging.getLogger(__name__)


# ==================== CUSTOM EXCEPTION CLASSES ====================

class BaseAPIException(APIException):
    """Base exception for all API errors with consistent response format."""
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "A server error occurred."
    default_error_code = "server_error"
    
    def __init__(
        self, 
        detail: Optional[str] = None, 
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        if status_code:
            self.status_code = status_code
        if error_code:
            self.default_error_code = error_code
        
        super().__init__(detail=detail)
        self.extra_data = extra_data or {}
    
    def get_response_data(self) -> Dict[str, Any]:
        """Generate standardized response data."""
        return {
            'status': 'error',
            'error': {
                'code': getattr(self, 'default_error_code', 'unknown_error'),
                'message': str(self.detail),
                'status_code': self.status_code,
            },
            'data': None,
            'timestamp': None,  # Set by middleware
            **self.extra_data
        }


class ValidationFailure(BaseAPIException):
    """Raised when data validation fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_error_code = "validation_error"
    default_detail = "Validation failed. Please check your input."


class ResourceNotFound(BaseAPIException):
    """Raised when a requested resource is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_error_code = "not_found"
    default_detail = "The requested resource was not found."


class AccessDenied(BaseAPIException):
    """Raised when user lacks required permissions."""
    status_code = status.HTTP_403_FORBIDDEN
    default_error_code = "forbidden"
    default_detail = "You do not have permission to perform this action."


class AuthenticationFailure(BaseAPIException):
    """Raised when authentication fails."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_error_code = "unauthorized"
    default_detail = "Authentication credentials were not provided or invalid."


class ConflictError(BaseAPIException):
    """Raised when there's a conflict (e.g., duplicate entry)."""
    status_code = status.HTTP_409_CONFLICT
    default_error_code = "conflict"
    default_detail = "The request conflicts with existing data."


class RateLimitExceeded(BaseAPIException):
    """Raised when rate limit is exceeded."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_error_code = "rate_limit_exceeded"
    default_detail = "Too many requests. Please try again later."


class ServiceUnavailable(BaseAPIException):
    """Raised when an external service is unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_error_code = "service_unavailable"
    default_detail = "The service is temporarily unavailable. Please try again later."


class InvalidOperationError(BaseAPIException):
    """Raised when an operation is invalid for the current state."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_error_code = "invalid_operation"
    default_detail = "This operation is not valid for the current state."


# ==================== RESPONSE WRAPPER ====================

class StandardResponse:
    """
    Standardized response wrapper ensuring consistent JSON structure across all endpoints.
    
    Response Format:
    {
        "status": "success|error",
        "data": {...} | null,
        "errors": [{...}] | null,
        "meta": {
            "timestamp": "ISO_8601",
            "request_id": "string",
            "version": "1.0"
        }
    }
    """
    
    def __init__(self, request=None):
        self.request = request
    
    def success(
        self, 
        data: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
        headers: Optional[Dict] = None
    ) -> Response:
        """Return a success response."""
        response_data = {
            'status': 'success',
            'data': data,
            'errors': None,
            'message': message,
            'meta': self._get_meta(),
        }
        return Response(response_data, status=status_code, headers=headers)
    
    def error(
        self,
        message: str,
        error_code: str = 'error',
        errors: Optional[list] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Response:
        """Return an error response."""
        response_data = {
            'status': 'error',
            'data': data,
            'errors': errors or [],
            'error': {
                'code': error_code,
                'message': message,
            },
            'meta': self._get_meta(),
        }
        return Response(response_data, status=status_code, headers=headers)
    
    def paginated(
        self,
        data: list,
        paginator=None,
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """Return a paginated response."""
        meta = self._get_meta()
        
        if paginator:
            meta['pagination'] = {
                'count': paginator.count if hasattr(paginator, 'count') else len(data),
                'next': paginator.get_next_link() if hasattr(paginator, 'get_next_link') else None,
                'previous': paginator.get_previous_link() if hasattr(paginator, 'get_previous_link') else None,
                'page_size': paginator.page_size if hasattr(paginator, 'page_size') else None,
            }
        
        response_data = {
            'status': 'success',
            'data': data,
            'message': message,
            'errors': None,
            'meta': meta,
        }
        return Response(response_data, status=status_code)
    
    def _get_meta(self) -> Dict[str, Any]:
        """Generate response metadata."""
        from django.utils import timezone
        
        meta = {
            'timestamp': timezone.now().isoformat(),
            'version': '1.0',
        }
        
        # Add request ID if available
        if self.request and hasattr(self.request, 'id'):
            meta['request_id'] = self.request.id
        
        return meta


# ==================== LOGGING UTILITIES ====================

class AuditLogger:
    """Centralized logging for audit trail and error tracking."""
    
    def __init__(self, logger_name: str = 'audit'):
        self.logger = logging.getLogger(logger_name)
        self.error_logger = logging.getLogger('errors')
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user=None,
        severity: str = 'ERROR'
    ):
        """Log error with context for debugging and audit."""
        context = context or {}
        
        log_data = {
            'error_type': error.__class__.__name__,
            'error_message': str(error),
            'user': user.email if user else 'anonymous',
            'timestamp': timezone.now().isoformat(),
            **context
        }
        
        # Log to error logger
        if severity == 'CRITICAL':
            self.error_logger.critical(log_data, exc_info=True)
        elif severity == 'WARNING':
            self.error_logger.warning(log_data)
        else:
            self.error_logger.error(log_data, exc_info=True)
    
    def log_audit_event(
        self,
        action: str,
        user=None,
        resource: Optional[str] = None,
        result: str = 'success',
        details: Optional[Dict] = None
    ):
        """Log audit event for compliance tracking."""
        from django.utils import timezone
        
        audit_data = {
            'action': action,
            'user': user.email if user else 'anonymous',
            'resource': resource,
            'result': result,
            'timestamp': timezone.now().isoformat(),
            'details': details or {}
        }
        
        self.logger.info(audit_data)


# ==================== CONVERSION UTILITIES ====================

def convert_drf_errors_to_standard_format(drf_errors: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert DRF validation errors to standardized error format.
    
    Converts from:
    {'field': ['error message']}
    
    To:
    {'field': {'code': 'error_code', 'message': 'error message'}}
    """
    formatted_errors = {}
    
    for field, error_list in drf_errors.items():
        if isinstance(error_list, list) and len(error_list) > 0:
            error_msg = str(error_list[0])
            formatted_errors[field] = {
                'message': error_msg,
                'code': 'validation_error',
            }
    
    return formatted_errors


# ==================== TIMEZONE UTILITIES ====================

def get_timezone():
    """Get configured timezone for consistent timestamps."""
    from django.utils import timezone
    return timezone.get_current_timezone()

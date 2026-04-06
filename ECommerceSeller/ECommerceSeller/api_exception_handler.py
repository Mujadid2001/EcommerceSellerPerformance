"""
Custom DRF exception handler for commercial-grade error responses.

This handler converts all DRF exceptions to a standardized JSON format
and ensures consistent error reporting across the entire API.
"""
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import ValidationError as DRFValidationError
import logging

from ECommerceSeller.exceptions import (
    StandardResponse, 
    convert_drf_errors_to_standard_format,
    AuditLogger
)

logger = logging.getLogger(__name__)
audit_logger = AuditLogger()


def custom_exception_handler(exc, context) -> Response:
    """
    Custom exception handler that returns standardized JSON responses.
    
    Response format:
    {
        "status": "error",
        "data": null,
        "errors": [...],
        "error": {
            "code": "error_code",
            "message": "Human-readable message"
        },
        "meta": {
            "timestamp": "ISO_8601",
            "request_id": "string"
        }
    }
    """
    
    request = context.get('request')
    view = context.get('view')
    response_wrapper = StandardResponse(request)
    
    # Log the exception
    _log_exception(exc, request, view)
    
    # Get the details from DRF's default handler
    response = drf_exception_handler(exc, context)
    
    # If DRF returns None, create a 500 response
    if response is None:
        return _handle_unexpected_error(exc, response_wrapper)
    
    # Transform response to standard format
    return _transform_response(exc, response, response_wrapper, request)


def _log_exception(exc: Exception, request, view):
    """Log exception with context for monitoring and debugging."""
    try:
        user = request.user if request and hasattr(request, 'user') else None
        
        context = {
            'view': view.__class__.__name__ if view else 'unknown',
            'method': request.method if request else 'unknown',
            'path': request.path if request else 'unknown',
            'remote_addr': _get_client_ip(request) if request else 'unknown',
        }
        
        severity = 'WARNING' if isinstance(exc, DRFValidationError) else 'ERROR'
        audit_logger.log_error(exc, context=context, user=user, severity=severity)
        
    except Exception as log_exc:
        logger.error(f"Failed to log exception: {log_exc}")


def _get_client_ip(request) -> str:
    """Extract client IP from request."""
    try:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    except:
        return 'unknown'


def _handle_unexpected_error(exc: Exception, response_wrapper: StandardResponse) -> Response:
    """Handle unexpected errors (not caught by DRF)."""
    
    # In production, don't expose internal details
    if hasattr(settings, 'DEBUG') and not settings.DEBUG:
        message = "An unexpected error occurred. Please try again later."
        error_code = "internal_error"
    else:
        message = str(exc)
        error_code = exc.__class__.__name__
    
    return response_wrapper.error(
        message=message,
        error_code=error_code,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def _transform_response(
    exc: Exception, 
    response: Response, 
    response_wrapper: StandardResponse,
    request
) -> Response:
    """Transform DRF response to standardized format."""
    
    # Extract status code from response
    http_status = response.status_code
    
    # Get the error detail and code
    error_detail = response.data
    error_code = _get_error_code(exc, http_status)
    error_message = _get_error_message(exc, error_detail)
    
    # Handle validation errors specially
    if http_status == status.HTTP_400_BAD_REQUEST:
        if isinstance(error_detail, dict):
            errors = convert_drf_errors_to_standard_format(error_detail)
            return response_wrapper.error(
                message=error_message,
                error_code=error_code,
                errors=errors,
                status_code=http_status
            )
    
    # Handle all other errors
    return response_wrapper.error(
        message=error_message,
        error_code=error_code,
        status_code=http_status
    )


def _get_error_code(exc: Exception, status_code: int) -> str:
    """Determine appropriate error code from exception type."""
    error_code_map = {
        'AuthenticationFailed': 'authentication_failed',
        'NotAuthenticated': 'not_authenticated',
        'PermissionDenied': 'permission_denied',
        'NotFound': 'not_found',
        'ValidationError': 'validation_error',
        'ParseError': 'parse_error',
        'Throttled': 'rate_limit_exceeded',
        'MethodNotAllowed': 'method_not_allowed',
        'NotAcceptable': 'not_acceptable',
        'UnsupportedMediaType': 'unsupported_media_type',
    }
    
    exc_class_name = exc.__class__.__name__
    return error_code_map.get(exc_class_name, 'api_error')


def _get_error_message(exc: Exception, error_detail) -> str:
    """Extract human-readable error message from exception."""
    
    if isinstance(error_detail, str):
        return error_detail
    
    if isinstance(error_detail, dict):
        # Try to get a generic error message
        if 'detail' in error_detail:
            return str(error_detail['detail'])
        # Otherwise, return first error found
        for key, value in error_detail.items():
            if isinstance(value, list) and value:
                return str(value[0])
            return str(value)
    
    if isinstance(error_detail, list) and error_detail:
        return str(error_detail[0])
    
    return str(exc.detail) if hasattr(exc, 'detail') else 'An error occurred'


# ==================== PRODUCTION/DEBUG HELPERS ====================

from django.conf import settings

def get_safe_error_message(exc: Exception, debug: bool) -> str:
    """
    Get error message safe for current environment.
    
    In production (DEBUG=False), hides internal details.
    In development (DEBUG=True), shows full error details for debugging.
    """
    if debug:
        return str(exc)
    
    # Production: generic message
    return "An error occurred processing your request."

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.conf import settings

def get_csrf_token(request):
    """Get CSRF token for frontend."""
    return JsonResponse({'csrfToken': get_token(request)})


def get_client_ip(request):
        """Extract client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return (
            x_forwarded_for.split(',')[0]
            if x_forwarded_for
            else request.META.get('REMOTE_ADDR')
        )


def get_frontend_url():
    """Get frontend base URL from settings or environment."""
    # Try to get from settings first, fallback to request scheme/host
    frontend_url = getattr(settings, 'FRONTEND_URL', None)
    if not frontend_url:
        # Default to localhost for development
        frontend_url = 'http://127.0.0.1:8000'
    return frontend_url.rstrip('/')


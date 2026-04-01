"""
Asynchronous tasks for authentication operations using Celery.
"""
import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from apps.authentication.models import EmailVerificationToken

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def send_verification_email_task(user_id, token_id=None):
    """
    Send verification email asynchronously using Celery.
    """
    try:
        user = User.objects.get(pk=user_id)
        
        # Generate token if not provided
        if token_id is None:
            token = EmailVerificationToken.objects.create(user=user)
        else:
            token = EmailVerificationToken.objects.get(pk=token_id)
        
        subject = "Email Verification - ECommerce Seller Performance"
        context = {
            'user': user,
            'token': token.token,
            'verification_url': f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/verify-email/{token.token}",
            'token_expiry_hours': settings.EMAIL_VERIFICATION_TIMEOUT_HOURS,
        }
        
        message = render_to_string('authentication/verify_email.html', context)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=message,
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent successfully to {user.email}")
        return {
            'status': 'email_sent',
            'user_id': user_id,
            'email': user.email
        }
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist")
        return {'status': 'failed', 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def send_password_reset_email(user_id):
    """
    Send password reset token to user.
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Generate reset token
        from django.contrib.auth.tokens import default_token_generator
        
        token = default_token_generator.make_token(user)
        
        # Send email
        subject = "Password Reset - ECommerce Seller Performance"
        context = {
            'user': user,
            'token': token,
            'reset_url': f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/reset-password/{token}",
        }
        
        message = render_to_string('authentication/reset_password_email.html', context)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=message,
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent to {user.email}")
        return {
            'status': 'email_sent',
            'user_id': user_id,
            'email': user.email
        }
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found.")
        return {'status': 'failed', 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending password reset email to user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def send_welcome_email(user_id):
    """
    Send welcome email to new user.
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Send email
        subject = f"Welcome to {getattr(settings, 'SITE_NAME', 'ECommerce Seller Performance')}!"
        context = {
            'user': user,
            'app_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
        }
        
        message = render_to_string('authentication/welcome_email.html', context)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=message,
            fail_silently=False,
        )
        
        logger.info(f"Welcome email sent to {user.email}")
        return {
            'status': 'email_sent',
            'user_id': user_id,
            'email': user.email
        }
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found.")
        return {'status': 'failed', 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending welcome email to user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_expired_verification_tokens(hours=48):
    """
    Delete expired email verification tokens.
    Runs hourly via Celery Beat.
    """
    try:
        cutoff_date = timezone.now() - timedelta(hours=hours)
        expired_tokens = EmailVerificationToken.objects.filter(created_at__lt=cutoff_date)
        count, _ = expired_tokens.delete()
        
        logger.info(f"Cleaned up {count} expired verification tokens.")
        return {'status': 'cleaned', 'count': count}
    except Exception as e:
        logger.error(f"Error cleaning up expired tokens: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def send_account_deactivation_confirmation(user_id):
    """
    Send account deactivation confirmation email.
    """
    try:
        user = User.objects.get(id=user_id)
        
        subject = "Account Deactivation Confirmation"
        context = {
            'user': user,
            'reactivate_url': f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/reactivate-account",
        }
        
        message = render_to_string('authentication/deactivation_email.html', context)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=message,
            fail_silently=False,
        )
        
        logger.info(f"Deactivation confirmation sent to {user.email}")
        return {
            'status': 'email_sent',
            'user_id': user_id,
        }
    except Exception as e:
        logger.error(f"Error sending deactivation email for user {user_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}

# If you're using Celery, uncomment below:
# from celery import shared_task
# 
# @shared_task
# def send_verification_email_celery(user_id, token_id):
#     """Celery task wrapper for sending verification email."""
#     return send_verification_email_task(user_id, token_id)


# If you're using Django-Q, uncomment below:
# This would be called like: async_task('apps.authentication.tasks.send_verification_email_task', user_id, token_id)

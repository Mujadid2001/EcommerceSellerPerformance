"""
Asynchronous tasks for authentication operations.
"""
import logging
from django.contrib.auth import get_user_model
from apps.authentication.models import EmailVerificationToken
from apps.authentication.email_utils import send_verification_email

User = get_user_model()
logger = logging.getLogger(__name__)


def send_verification_email_task(user_id, token_id):
    """
    Send verification email asynchronously.
    
    This function can be used with Celery, Django-Q, or any task queue.
    For now, it's a regular function that can be called synchronously
    or wrapped in your preferred task queue.
    
    Args:
        user_id: The user's primary key
        token_id: The verification token's primary key
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        user = User.objects.get(pk=user_id)
        token = EmailVerificationToken.objects.get(pk=token_id)
        
        result = send_verification_email(user, token)
        
        if result:
            logger.info(f"Verification email sent successfully to {user.email}")
        else:
            logger.error(f"Failed to send verification email to {user.email}")
        
        return result
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist")
        return False
    except EmailVerificationToken.DoesNotExist:
        logger.error(f"Token with id {token_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        return False


# If you're using Celery, uncomment below:
# from celery import shared_task
# 
# @shared_task
# def send_verification_email_celery(user_id, token_id):
#     """Celery task wrapper for sending verification email."""
#     return send_verification_email_task(user_id, token_id)


# If you're using Django-Q, uncomment below:
# This would be called like: async_task('apps.authentication.tasks.send_verification_email_task', user_id, token_id)

"""
Email utilities for sending verification and notification emails.
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from apps.authentication.utils import get_frontend_url


logger = logging.getLogger(__name__)

SYSTEM_NAME = "E-Commerce Seller Performance"
YEAR = "2026"
SYSTEM_ICON = "🛒"


def send_verification_email(user, token):
    """
    Send email verification link to user.
    
    Args:
        user: User instance
        token: EmailVerificationToken instance
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = f'Verify Your Email - {SYSTEM_NAME}'
        
        # Verification token to be used by frontend
        verification_token = str(token.token)
        
        # Create verification link for frontend
        frontend_url = get_frontend_url()
        verification_link = f"{frontend_url}/verify-email?token={verification_token}"
        
        # Create HTML message with clickable link
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    margin: 20px 0;
                    background-color: #2563eb;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                .button:hover {{ background-color: #1d4ed8; }}
                .token-box {{ 
                    background-color: #f0f0f0; 
                    border: 1px solid #2563eb; 
                    padding: 15px; 
                    margin: 20px 0; 
                    text-align: center; 
                    font-family: monospace; 
                    font-size: 12px; 
                    word-break: break-all;
                    border-radius: 5px;
                }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
                .info {{ background-color: #e0f2fe; padding: 10px; border-left: 4px solid #0284c7; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{SYSTEM_ICON} Welcome to {SYSTEM_NAME}!</h1>
                </div>
                <div class="content">
                    <h2>Hello {user.get_full_name() or user.email},</h2>
                    <p>Thank you for registering with {SYSTEM_NAME}. Please verify your email address to complete your registration and access the system.</p>
                    
                    <div style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email Address</a>
                    </div>
                    
                    <p style="text-align: center; color: #666; font-size: 12px;">Or copy this link:</p>
                    <div class="token-box">
                        <a href="{verification_link}" style="color: #2563eb; text-decoration: none; word-wrap: break-word;">{verification_link}</a>
                    </div>
                    
                    <div class="info">
                        <strong>Verification Token (if link doesn't work):</strong><br>
                        {verification_token}
                    </div>
                    
                    <p><strong>⏰ This link will expire in 48 hours.</strong></p>
                    <p>If you didn't create an account, please ignore this email and your account will not be activated.</p>
                </div>
                <div class="footer">
                    <p>&copy; {YEAR} {SYSTEM_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create plain text version
        plain_message = f"""
Hello {user.get_full_name() or user.email},

Thank you for registering with {SYSTEM_NAME}. Please verify your email address to complete your registration.

Click the link below to verify your email:
{verification_link}

Or copy and paste this verification token in the application:
{verification_token}

This link will expire in 48 hours.

If you didn't create an account, please ignore this email.

© {YEAR} {SYSTEM_NAME}. All rights reserved.
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False


def send_verification_success_email(user):
    """
    Send email confirmation after successful verification.
    
    Args:
        user: User instance
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = f'Email Verified Successfully - {SYSTEM_NAME}'
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Email Verified!</h1>
                </div>
                <div class="content">
                    <h2>Hello {user.get_full_name()},</h2>
                    <p>Your email address has been successfully verified!</p>
                    <p>You can now access all features of the {SYSTEM_NAME}.</p>
                    <p>Thank you for completing your registration.</p>
                </div>
                <div class="footer">
                    <p>&copy; {YEAR} {SYSTEM_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = f"""
        Hello {user.get_full_name()},
        
        Your email address has been successfully verified!
        
        You can now access all features of the {SYSTEM_NAME}.
        
        Thank you for completing your registration.
        
        © {YEAR} {SYSTEM_NAME}. All rights reserved.
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Verification success email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification success email to {user.email}: {e}")
        return False


def resend_verification_email(user):
    """
    Resend verification email to user.
    
    Args:
        user: User instance
    
    Returns:
        dict: Result with success status and message
    """
    from apps.authentication.models import EmailVerificationToken
    
    if user.is_verified:
        return {
            'success': False,
            'message': 'Email is already verified.'
        }
    
    # Invalidate old tokens
    EmailVerificationToken.objects.filter(
        user=user,
        is_used=False
    ).update(is_used=True)
    
    # Create new token
    token = EmailVerificationToken.objects.create(user=user)
    
    # Send email
    email_sent = send_verification_email(user, token)
    
    if email_sent:
        return {
            'success': True,
            'message': 'Verification email sent successfully.'
        }
    else:
        return {
            'success': False,
            'message': 'Failed to send verification email. Please try again.'
        }

"""
Views for authentication endpoints.
"""
import contextlib
import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout, get_user_model
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from apps.authentication.serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    UserUpdateSerializer, ChangePasswordSerializer, LoginLogSerializer,
    EmailVerificationSerializer, ResendVerificationSerializer
)
from apps.authentication.models import LoginLog, EmailVerificationToken
from apps.authentication.email_utils import (
    send_verification_email, send_verification_success_email, resend_verification_email
)
from apps.authentication.permissions import IsAdmin
from apps.authentication.utils import get_client_ip
from apps.authentication.tasks import send_verification_email_task

User = get_user_model()
logger = logging.getLogger(__name__)


class AuthenticationViewSet(viewsets.ViewSet):
    """
    ViewSet for authentication operations.
    Public endpoints for registration, login, and email verification.
    """
    permission_classes = [AllowAny]  # Override default permissions for all actions
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """
        Register new user with proper error handling and atomicity.
        Handles user creation, token generation, and sending verification email.
        Args:
            request: HTTP request with user registration data.
        Returns:
            Response: HTTP response with registration result.
        """
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Use atomic transaction to ensure data integrity
                with transaction.atomic():
                    # Create user
                    user = serializer.save()
                    
                    # Create verification token
                    token = EmailVerificationToken.objects.create(user=user)
                    
                    logger.info(f"New user registered: {user.email} as {user.role}")
                
                # Send email synchronously
                # For production, consider using Celery or similar for async email sending
                # If email fails, user is still created and can request resend
                email_sent = False
                try:
                    # Send verification email
                    send_verification_email_task(user.id, token.id)
                    email_sent = True
                    logger.info(f"Verification email sent for {user.email}")
                except Exception as e:
                    # Email send failed but user is created
                    logger.error(f"Failed to send verification email for {user.email}: {str(e)}")
                    email_sent = False
                
                # Prepare response message
                message = _('Registration successful. Please check your email to verify your account.')
                if not email_sent:
                    message = _('Registration successful, but verification email could not be sent. Please request a new verification email.')
                return Response(
                    {
                        'message': message,
                        'user': UserSerializer(user).data,
                        'email_sent': email_sent
                    },
                    status=status.HTTP_201_CREATED
                )
            
            except Exception as e:
                # Log the error and return appropriate response
                logger.error(f"Registration failed: {str(e)}")
                return Response(
                    {'error': _('Registration failed. Please try again later.')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """Login user."""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            ip = get_client_ip(request)

            # Check if email is verified (mandatory in production, optional in development)
            from django.conf import settings
            if not user.is_verified and not settings.DEBUG:
                return Response(
                    {
                        'error': _('Please verify your email address before logging in.'),
                        'requires_verification': True
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # No teacher approval logic needed

            # Log successful login
            LoginLog.objects.create(
                user=user,
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True
            )

            # Login user with session authentication (not JWT)
            login(request, user)
            
            # Update last login timestamp
            user.update_last_login()
            
            logger.info(f"User logged in: {user.email}")

            return Response(
                {
                    'message': _('Login successful.'),
                    'user': UserSerializer(user).data,
                    'is_verified': user.is_verified
                },
                status=status.HTTP_200_OK
            )

        # Log failed login attempt
        if email := request.data.get('email'):
            with contextlib.suppress(User.DoesNotExist):
                user = User.objects.get(email=email)
                ip = get_client_ip(request)
                LoginLog.objects.create(
                    user=user,
                    ip_address=ip,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=False,
                    failure_reason='Invalid password'
                )
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Logout user."""
        user_email = request.user.email
        logout(request)
        logger.info(f"User logged out: {user_email}")
        return Response(
            {'message': _('Logout successful.')},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current user details."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated], url_path='profile-update')
    def profile_update(self, request):
        """Update user profile."""
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            logger.info(f"User profile updated: {request.user.email}")
            return Response(
                {
                    'message': _('Profile updated successfully.'),
                    'user': UserSerializer(request.user).data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='change-password')
    def change_password(self, request):
        """Change user password."""
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'error': _('Old password is incorrect.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            logger.info(f"Password changed for user: {user.email}")
            
            return Response(
                {'message': _('Password changed successfully.')},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated, IsAdmin]
    )
    def login_logs(self, request):
        """Get login logs (admin only)."""
        logs = LoginLog.objects.all().order_by('-timestamp')
        
        # Pagination
        page = request.query_params.get('page', 1)
        page_size = 20
        start = (int(page) - 1) * page_size
        end = start + page_size
        
        serializer = LoginLogSerializer(logs[start:end], many=True)
        return Response(
            {
                'count': logs.count(),
                'results': serializer.data
            }
        )
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny], url_path='verify-email')
    def verify_email(self, request):
        """Verify user email with token."""
        from django.utils.decorators import method_decorator
        from django.views.decorators.csrf import csrf_exempt
        
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            user = token.user
            
            # Mark token as used
            token.is_used = True
            token.save()
            
            # Mark user as verified
            user.is_verified = True
            user.save()
            
            # Send success email
            send_verification_success_email(user)
            
            logger.info(f"Email verified for user: {user.email}")
            
            return Response(
                {
                    'message': _('Email verified successfully! You can now log in.'),
                    'user': UserSerializer(user).data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def resend_verification(self, request):
        """Resend verification email."""
        serializer = ResendVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['email']
            
            # Use the utility function to resend
            result = resend_verification_email(user)
            
            if result['success']:
                logger.info(f"Verification email resent to: {user.email}")
                return Response(
                    {'message': result['message']},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': result['message']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def verification_status(self, request):
        """Get email verification status for current user."""
        user = request.user
        return Response(
            {
                'is_verified': user.is_verified,
                'email': user.email,
                'user': UserSerializer(user).data
            },
            status=status.HTTP_200_OK
        )


class UserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for user management (admin only)."""
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        """Filter users by role if specified."""
        queryset = User.objects.all()
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        return queryset
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate user account."""
        user = self.get_object()
        user.is_active = True
        user.save()
        logger.info(f"User activated: {user.email}")
        return Response({'message': _('User activated.')})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate user account."""
        user = self.get_object()
        user.is_active = False
        user.save()
        logger.info(f"User deactivated: {user.email}")
        return Response({'message': _('User deactivated.')})
    
    # All teacher-related actions removed
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate user account."""
        user = self.get_object()
        user.is_active = False
        user.save()
        logger.info(f"User deactivated: {user.email}")
        return Response({'message': _('User deactivated.')})
    
    def destroy(self, request, *args, **kwargs):
        """Delete user account."""
        user = self.get_object()
        email = user.email
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"User deleted: {email}")
        return response


# Web views for authentication
def login_view(request):
    """Render login page."""
    if request.user.is_authenticated:
        return redirect('performance:dashboard')
    return render(request, 'authentication/login.html')


def register_view(request):
    """Render registration page."""
    if request.user.is_authenticated:
        return redirect('performance:dashboard')
    return render(request, 'authentication/register.html')


def verify_email_view(request):
    """Render email verification page."""
    return render(request, 'authentication/email_verification.html')


def logout_view(request):
    """Logout user."""
    from django.contrib.auth import logout as django_logout
    django_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

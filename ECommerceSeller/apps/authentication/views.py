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
from django_q.tasks import async_task
User = get_user_model()
logger = logging.getLogger(__name__)


class AuthenticationViewSet(viewsets.ViewSet):
    """ViewSet for authentication operations."""
    
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
                
                # Send email asynchronously using Django-Q
                # This prevents blocking the HTTP response
                # If email fails, user is still created and can request resend
                email_sent = False
                try:
                    # Queue the email task for background processing
                    async_task(
                        'apps.authentication.tasks.send_verification_email_task',
                        user.id,
                        token.id,
                        task_name=f'verification_email_{user.email}',
                    )
                    email_sent = True
                    logger.info(f"Verification email queued for {user.email}")
                except Exception as e:
                    # Email queue failed but user is created
                    logger.error(f"Failed to queue verification email for {user.email}: {str(e)}")
                    email_sent = False
                
                # Prepare response message
                if user.role == User.Role.ADMIN:
                    message = _('Registration successful! Your account is admin account')
                else:
                    message = _('Registration successful. Please check your email to verify your account.')
                    if not email_sent:
                        message = _('Registration successful, but verification email could not be sent. Please request a new verification email.')
                
                return Response(
                    {
                        'message': message,
                        'user': UserSerializer(user).data,
                        'email_sent': email_sent,
                        'requires_approval': user.role == User.Role.TEACHER and not user.is_approved
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
            
            # Check if teacher account is approved
            if user.role == User.Role.TEACHER and not user.is_approved:
                return Response(
                    {
                        'error': _('Your teacher account is pending admin approval. Please wait for approval to access the system.'),
                        'requires_approval': True
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            # Log successful login
            LoginLog.objects.create(
                user=user,
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True
            )

            # Generate JWT tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            login(request, user)
            logger.info(f"User logged in: {user.email}")

            return Response(
                {
                    'message': _('Login successful.'),
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    },
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
    
    @action(detail=True, methods=['post'])
    def approve_teacher(self, request, pk=None):
        """Approve a pending teacher account."""
        user = self.get_object()
        
        if user.role != User.Role.TEACHER:
            return Response(
                {'error': _('User is not a teacher.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.is_approved:
            return Response(
                {'error': _('Teacher is already approved.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_approved = True
        user.save()
        
        logger.info(f"Teacher approved: {user.email} by {request.user.email}")
        
        # Send approval notification email
        email_sent = send_teacher_approval_email(user, approved_by=request.user)
        
        return Response({
            'message': _('Teacher account approved successfully.'),
            'user': UserSerializer(user).data,
            'email_sent': email_sent
        })
    
    @action(detail=True, methods=['post'])
    def reject_teacher(self, request, pk=None):
        """Reject a pending teacher account (delete)."""
        user = self.get_object()
        
        if user.role != User.Role.TEACHER:
            return Response(
                {'error': _('User is not a teacher.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email = user.email
        user.delete()
        
        logger.info(f"Teacher rejected and deleted: {email} by {request.user.email}")
        
        # TODO: Send rejection notification email
        
        return Response({'message': _('Teacher account rejected and removed.')})
    
    @action(detail=False, methods=['get'])
    def pending_teachers(self, request):
        """Get list of teachers pending approval."""
        pending = User.objects.filter(
            role=User.Role.TEACHER,
            is_approved=False
        ).order_by('-created_at')
        
        serializer = UserSerializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate_teacher_code(self, request):
        """Generate a new teacher verification code (deprecated - no longer used)."""
        return Response(
            {'error': _('Teacher verification codes are no longer used. Teachers must be approved by administrators.')},
            status=status.HTTP_410_GONE
        )
        
        return Response(
            {'error': _('Teacher verification codes are no longer used. Teachers must be approved by administrators.')},
            status=status.HTTP_410_GONE
        )
    
    @action(detail=False, methods=['get'])
    def verification_codes(self, request):
        """Get list of all teacher verification codes (deprecated - no longer used)."""
        return Response(
            {'error': _('Teacher verification codes are no longer used. Teachers must be approved by administrators.')},
            status=status.HTTP_410_GONE
        )
    
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

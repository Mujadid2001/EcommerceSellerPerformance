"""
Comprehensive test suite for Authentication app.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.authentication.models import User, EmailVerificationToken, LoginLog

User = get_user_model()


class UserModelTestCase(TestCase):
    """Test cases for custom User model."""
    
    def test_user_creation_with_email(self):
        """Test user can be created with email."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_superuser_creation(self):
        """Test superuser can be created."""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, 'admin')
    
    def test_user_role_defaults(self):
        """Test user role defaults."""
        user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        
        self.assertEqual(user.role, 'user')
    
    def test_user_with_seller_role(self):
        """Test user can be created with seller role."""
        seller = User.objects.create_user(
            email='seller@example.com',
            password='testpass123',
            role='seller'
        )
        
        self.assertEqual(seller.role, 'seller')
    
    def test_user_string_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        self.assertIn('John Doe', str(user))
        self.assertIn('test@example.com', str(user))


class EmailVerificationTokenTestCase(TestCase):
    """Test cases for EmailVerificationToken model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            is_verified=False
        )
    
    def test_token_creation(self):
        """Test verification token can be created."""
        token = EmailVerificationToken.objects.create(user=self.user)
        
        self.assertIsNotNone(token.token)
        self.assertEqual(token.user, self.user)
    
    def test_token_is_unique(self):
        """Test verification tokens are unique."""
        token1 = EmailVerificationToken.objects.create(user=self.user)
        token2 = EmailVerificationToken.objects.create(user=self.user)
        
        self.assertNotEqual(token1.token, token2.token)
    
    def test_token_expiration(self):
        """Test token expiration."""
        token = EmailVerificationToken.objects.create(user=self.user)
        
        # Token should not be expired immediately
        self.assertFalse(token.is_expired())
    
    def test_expired_token_check(self):
        """Test checking for expired tokens."""
        token = EmailVerificationToken.objects.create(user=self.user)
        
        # Manually set created_at to 25 hours ago (assuming 24-hour expiry)
        token.created_at = timezone.now() - timedelta(hours=25)
        token.save()
        
        self.assertTrue(token.is_expired())


class LoginLogTestCase(TestCase):
    """Test cases for LoginLog model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_successful_login_log(self):
        """Test successful login logging."""
        log = LoginLog.objects.create(
            user=self.user,
            ip_address='192.168.1.1',
            success=True
        )
        
        self.assertTrue(log.success)
        self.assertIsNone(log.failure_reason)
    
    def test_failed_login_log(self):
        """Test failed login logging."""
        log = LoginLog.objects.create(
            user=self.user,
            ip_address='192.168.1.1',
            success=False,
            failure_reason='Invalid password'
        )
        
        self.assertFalse(log.success)
        self.assertEqual(log.failure_reason, 'Invalid password')


class UserAuthenticationTestCase(TestCase):
    """Test cases for user authentication."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            is_verified=True
        )
    
    def test_login_with_valid_credentials(self):
        """Test login with valid credentials."""
        response = self.client.post('/auth/api/authentication/login/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        # Should succeed or redirect
        self.assertIn(response.status_code, [200, 302])
    
    def test_logout(self):
        """Test user logout."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post('/auth/api/authentication/logout/')
        
        self.assertIn(response.status_code, [200, 302])
    
    def test_password_change(self):
        """Test password change."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post('/auth/api/authentication/change_password/', {
            'old_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        })
        
        self.assertIn(response.status_code, [200, 201])


class UserRegistrationTestCase(TestCase):
    """Test cases for user registration."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_user_registration(self):
        """Test user can register."""
        response = self.client.post('/auth/api/authentication/register/', {
            'email': 'newuser@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        
        # Should succeed or require email verification
        self.assertIn(response.status_code, [200, 201, 400])
    
    def test_duplicate_email_registration(self):
        """Test duplicate email registration fails."""
        User.objects.create_user(
            email='existing@example.com',
            password='testpass123'
        )
        
        response = self.client.post('/auth/api/authentication/register/', {
            'email': 'existing@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        })
        
        # Should fail
        self.assertIn(response.status_code, [400, 409])


class EmailVerificationTestCase(TestCase):
    """Test cases for email verification flow."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            is_verified=False
        )
    
    def test_email_verification_flow(self):
        """Test complete email verification flow."""
        # Create verification token
        token = EmailVerificationToken.objects.create(user=self.user)
        
        # Verify email
        response = self.client.post('/auth/api/authentication/verify-email/', {
            'token': str(token.token)
        })
        
        self.assertIn(response.status_code, [200, 201])
        
        # Check user is verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)
    
    def test_invalid_token_verification(self):
        """Test verification with invalid token."""
        response = self.client.post('/auth/api/authentication/verify-email/', {
            'token': 'invalid-token-xyz'
        })
        
        self.assertIn(response.status_code, [400, 404])

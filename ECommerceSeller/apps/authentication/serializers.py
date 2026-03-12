"""
Serializers for authentication endpoints.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _
from apps.authentication.models import LoginLog, EmailVerificationToken

User = get_user_model()

# ModelSerializers
class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for seller registration with business information."""
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='Minimum 8 characters'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='Confirm your password'
    )
    business_name = serializers.CharField(
        write_only=True,
        max_length=255,
        help_text='Your business or store name'
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'password', 'password_confirm', 'business_name'
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone': {'required': False},
        }
    
    def validate(self, data):
        """Validate passwords match and business name."""
        if data.get('password') != data.pop('password_confirm'):
            raise serializers.ValidationError(
                _("Passwords don't match.")
            )
        
        # Validate business name
        business_name = data.get('business_name', '').strip()
        if not business_name:
            raise serializers.ValidationError(
                {"business_name": _("Business name is required.")}
            )
        
        return data
    
    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                _("Email address already registered.")
            )
        return value
    
    def create(self, validated_data):
        """Create new seller user with business profile."""
        # Extract business name
        business_name = validated_data.pop('business_name')
        
        # Create user with SELLER role for seller registration
        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone'),
            role=User.Role.SELLER,
            password=validated_data['password'],
        )
        
        # Store business_name temporarily for the signal to use
        user._business_name = business_name
        user.save()
        
        return user
        

class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details."""
    
    role_display = serializers.CharField(
        source='get_role_display_verbose',
        read_only=True
    )
    full_name = serializers.CharField(
        source='get_full_name',
        read_only=True
    )
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'role_display', 'profile_picture', 'is_active', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for user profile updates."""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'profile_picture'
        ]



class LoginLogSerializer(serializers.ModelSerializer):
    """Serializer for login logs."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = LoginLog
        fields = [
            'id', 'user', 'user_email', 'ip_address', 'success',
            'failure_reason', 'timestamp'
        ]
        read_only_fields = fields


# Simple Serializers
class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})
    
    def validate(self, data):
        """Authenticate user."""
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            user = authenticate(
                username=email,
                password=password
            )
            if not user:
                raise serializers.ValidationError(
                    _("Invalid email or password.")
                )
            data['user'] = user
        else:
            raise serializers.ValidationError(
                _("Email and password are required.")
            )
        
        return data





class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    old_password = serializers.CharField(
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        min_length=8,
        style={'input_type': 'password'}
    )
    
    def validate(self, data):
        """Validate passwords."""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError(
                _("New passwords don't match.")
            )
        return data

class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""
    
    token = serializers.UUIDField(required=True)
    
    def validate_token(self, value):
        """Validate verification token."""
        try:
            token = EmailVerificationToken.objects.get(token=value)

            if token.is_used:
                raise serializers.ValidationError(
                    _("This verification link has already been used.")
                )

            if token.is_expired():
                raise serializers.ValidationError(
                    _("This verification link has expired. Please request a new one.")
                )

            return token

        except EmailVerificationToken.DoesNotExist as e:
            raise serializers.ValidationError(
                _("Invalid verification token.")
            ) from e


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resending verification email."""
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Validate email exists."""
        try:
            user = User.objects.get(email=value)
            if user.is_verified:
                raise serializers.ValidationError(
                    _("This email is already verified.")
                )
            return user
        except User.DoesNotExist as e:
            raise serializers.ValidationError(
                _("No account found with this email address.")
            ) from e

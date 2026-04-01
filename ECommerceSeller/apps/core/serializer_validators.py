"""
Commercial-grade serializer validators and utilities.

Implements strict validation patterns:
- Explicit field definitions (never use fields = '__all__')
- Custom validate_<field> methods for all business constraints
- Reusable validator functions
- Type-safe field conversion utilities
- ISO 8601 date/time formatting
- Decimal precision for financial data
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from typing import Optional, Any, Callable, Dict, List
from django.core.validators import (
    EmailValidator as DjangoEmailValidator,
    URLValidator,
    RegexValidator,
    MinValueValidator,
    MaxValueValidator,
)
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


# ==================== DECIMAL VALIDATORS ====================

class DecimalValidator:
    """Validator for decimal fields ensuring precise financial data handling."""
    
    def __init__(self, max_digits: int = 10, decimal_places: int = 2):
        self.max_digits = max_digits
        self.decimal_places = decimal_places
    
    def __call__(self, value: Any) -> Decimal:
        """Validate and convert to Decimal."""
        try:
            if isinstance(value, Decimal):
                result = value
            else:
                result = Decimal(str(value))
            
            # Validate precision
            sign, digits, exponent = result.as_tuple()
            
            # Check total digits
            total_digits = len(digits)
            if total_digits > self.max_digits:
                raise ValidationError(
                    f"Ensure this value has at most {self.max_digits} digits. "
                    f"Got {total_digits}."
                )
            
            # Round to correct decimal places
            return result.quantize(
                Decimal(10) ** -self.decimal_places,
                rounding=ROUND_HALF_UP
            )
        
        except (InvalidOperation, TypeError) as e:
            raise ValidationError(f"Invalid decimal value: {value}")


class MoneyValidator:
    """Validator for monetary values with strict rules."""
    
    def __init__(self, min_value: Decimal = Decimal('0.01')):
        self.min_value = min_value
    
    def __call__(self, value: Any) -> Decimal:
        """Validate monetary value."""
        if value is None:
            return None
        
        converter = DecimalValidator(max_digits=12, decimal_places=2)
        decimal_value = converter(value)
        
        if decimal_value < self.min_value:
            raise ValidationError(
                f"Monetary value must be at least {self.min_value}. "
                f"Got {decimal_value}."
            )
        
        return decimal_value


class PercentageValidator:
    """Validator for percentage fields (0-100)."""
    
    def __call__(self, value: Any) -> Decimal:
        """Validate percentage value."""
        if value is None:
            return None
        
        converter = DecimalValidator(max_digits=5, decimal_places=2)
        decimal_value = converter(value)
        
        if not (Decimal('0.00') <= decimal_value <= Decimal('100.00')):
            raise ValidationError(
                "Percentage must be between 0.00 and 100.00. "
                f"Got {decimal_value}."
            )
        
        return decimal_value


class RatingValidator:
    """Validator for rating fields (1-5 stars)."""
    
    def __call__(self, value: Any) -> Decimal:
        """Validate rating value."""
        if value is None:
            return None
        
        converter = DecimalValidator(max_digits=3, decimal_places=2)
        decimal_value = converter(value)
        
        if not (Decimal('1.00') <= decimal_value <= Decimal('5.00')):
            raise ValidationError(
                "Rating must be between 1.00 and 5.00 stars. "
                f"Got {decimal_value}."
            )
        
        return decimal_value


# ==================== DATE/TIME VALIDATORS ====================

class ISODateTimeValidator:
    """
    Validator for ISO 8601 datetime fields.
    Ensures consistent datetime handling across the API.
    """
    
    def __call__(self, value: Any) -> datetime:
        """Validate and return ISO datetime."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                # Try ISO format with timezone
                if value.endswith('Z'):
                    value = value[:-1] + '+00:00'
                dt = datetime.fromisoformat(value)
                # Ensure timezone aware
                if dt.tzinfo is None:
                    dt = timezone.make_aware(dt)
                return dt
            except (ValueError, TypeError) as e:
                raise ValidationError(
                    f"Invalid ISO 8601 datetime format: {value}. "
                    f"Expected format: YYYY-MM-DDTHH:MM:SS[.ffffff][+HH:MM]"
                )
        
        raise ValidationError(f"Expected string or datetime, got {type(value)}")


class ISODateValidator:
    """Validator for ISO 8601 date fields."""
    
    def __call__(self, value: Any) -> date:
        """Validate and return ISO date."""
        if value is None:
            return None
        
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except (ValueError, TypeError):
                raise ValidationError(
                    f"Invalid ISO 8601 date format: {value}. "
                    f"Expected format: YYYY-MM-DD"
                )
        
        raise ValidationError(f"Expected string or date, got {type(value)}")


class DateNotInFutureValidator:
    """Validator ensuring date is not in the future."""
    
    def __init__(self, allow_today: bool = True):
        self.allow_today = allow_today
    
    def __call__(self, value: any):
        """Validate date is not in future."""
        if value is None:
            return
        
        if isinstance(value, str):
            value = ISODateValidator()(value)
        
        today = timezone.now().date() if isinstance(value, date) and not isinstance(value, datetime) else timezone.now()
        
        if isinstance(value, datetime):
            if self.allow_today:
                max_allowed = timezone.now() + timedelta(minutes=5)
            else:
                max_allowed = timezone.now()
            if value > max_allowed:
                raise ValidationError("Date/time cannot be in the future.")
        else:
            if self.allow_today and value > today:
                raise ValidationError("Date cannot be in the future.")


# ==================== EMAIL VALIDATORS ====================

class CommercialEmailValidator:
    """Enhanced email validator with business logic."""
    
    def __init__(self, reject_disposable: bool = False):
        self.reject_disposable = reject_disposable
        self.base_validator = DjangoEmailValidator()
    
    def __call__(self, value: str):
        """Validate email address."""
        if not value:
            raise ValidationError("Email address is required.")
        
        # Basic email validation
        try:
            self.base_validator(value)
        except ValidationError:
            raise ValidationError(f"Invalid email address: {value}")
        
        # Reject disposable emails if configured
        if self.reject_disposable:
            if self._is_disposable_email(value):
                raise ValidationError(
                    "Disposable email addresses are not allowed. "
                    "Please use a permanent email address."
                )
        
        return value.lower()
    
    @staticmethod
    def _is_disposable_email(email: str) -> bool:
        """Check if email is from a disposable email service."""
        disposable_domains = {
            'tempmail.com', '10minutemail.com', 'guerrillamail.com',
            'throwaway.email', 'maildrop.cc', 'mailinator.com',
            'temp-mail.org', 'temp-mail.io',
        }
        
        domain = email.split('@')[1].lower()
        return domain in disposable_domains


# ==================== STRING VALIDATORS ====================

class BusinessNameValidator:
    """Validator for business names."""
    
    def __call__(self, value: str):
        """Validate business name."""
        if not value or not value.strip():
            raise ValidationError("Business name is required.")
        
        value = value.strip()
        
        if len(value) < 3:
            raise ValidationError("Business name must be at least 3 characters.")
        
        if len(value) > 255:
            raise ValidationError("Business name must not exceed 255 characters.")
        
        # Check for valid characters
        invalid_chars = ['<', '>', '&', '"', "'", ';', '\\']
        if any(char in value for char in invalid_chars):
            raise ValidationError("Business name contains invalid characters.")
        
        return value


class RegistrationNumberValidator:
    """Validator for business registration numbers."""
    
    def __call__(self, value: str):
        """Validate registration number."""
        if not value or not value.strip():
            raise ValidationError("Registration number is required.")
        
        value = value.strip().upper()
        
        if len(value) < 3:
            raise ValidationError("Registration number must be at least 3 characters.")
        
        if len(value) > 100:
            raise ValidationError("Registration number must not exceed 100 characters.")
        
        # Allow alphanumeric and hyphens
        if not all(c.isalnum() or c in ['-', '_'] for c in value):
            raise ValidationError("Registration number contains invalid characters.")
        
        return value


# ==================== RELATIONSHIP VALIDATORS ====================

class DateSequenceValidator:
    """Validator for ensuring correct date sequences."""
    
    def __init__(self, before_field: str, after_field: str):
        """
        Args:
            before_field: Field name that should come first
            after_field: Field name that should come after
        """
        self.before_field = before_field
        self.after_field = after_field
    
    def __call__(self, attrs: Dict[str, Any]):
        """Validate date sequence."""
        before_value = attrs.get(self.before_field)
        after_value = attrs.get(self.after_field)
        
        if before_value and after_value:
            if after_value < before_value:
                raise ValidationError({
                    self.after_field: (
                        f"{self.after_field} must be after {self.before_field}. "
                        f"Got {self.after_field}={after_value}, "
                        f"{self.before_field}={before_value}"
                    )
                })


class StatusTransitionValidator:
    """Validator for valid status transitions."""
    
    def __init__(self, valid_transitions: Dict[str, List[str]]):
        """
        Args:
            valid_transitions: Dict mapping from_status -> [to_status1, to_status2, ...]
        """
        self.valid_transitions = valid_transitions
    
    def __call__(self, instance, current_status: str, new_status: str):
        """Validate status transition."""
        if current_status not in self.valid_transitions:
            raise ValidationError(f"Unknown status: {current_status}")
        
        allowed_transitions = self.valid_transitions[current_status]
        if new_status not in allowed_transitions:
            raise ValidationError(
                f"Cannot transition from {current_status} to {new_status}. "
                f"Allowed transitions: {', '.join(allowed_transitions)}"
            )


# ==================== REUSABLE FIELD CONVERTERS ====================

class FieldConverters:
    """Utility class for type-safe field conversions."""
    
    @staticmethod
    def to_iso_datetime(value: Any) -> str:
        """Convert any datetime to ISO 8601 string."""
        validator = ISODateTimeValidator()
        dt = validator(value)
        return dt.isoformat() if dt else None
    
    @staticmethod
    def to_iso_date(value: Any) -> str:
        """Convert any date to ISO 8601 string."""
        validator = ISODateValidator()
        d = validator(value)
        return d.isoformat() if d else None
    
    @staticmethod
    def to_decimal(value: Any, max_digits: int = 10, decimal_places: int = 2) -> Decimal:
        """Convert any numeric value to Decimal."""
        validator = DecimalValidator(max_digits, decimal_places)
        return validator(value)
    
    @staticmethod
    def to_money(value: Any) -> Decimal:
        """Convert to monetary Decimal (12.2 precision)."""
        validator = MoneyValidator()
        return validator(value)
    
    @staticmethod
    def to_percentage(value: Any) -> Decimal:
        """Convert to percentage Decimal (0-100)."""
        validator = PercentageValidator()
        return validator(value)
    
    @staticmethod
    def to_rating(value: Any) -> Decimal:
        """Convert to rating Decimal (1-5)."""
        validator = RatingValidator()
        return validator(value)


# ==================== STANDARDIZED SERIALIZER BASE ====================

class StrictModelSerializer(serializers.ModelSerializer):
    """
    Base serializer enforcing commercial-grade standards:
    - Explicit fields (never __all__)
    - Proper field types
    - Custom validators
    - Consistent error messages
    """
    
    # Override to ensure explicit field definitions
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validate_explicit_fields()
    
    def _validate_explicit_fields(self):
        """Ensure fields are explicitly defined."""
        if hasattr(self.Meta, 'fields') and self.Meta.fields == '__all__':
            raise AssertionError(
                f"{self.__class__.__name__}: Use of fields='__all__' is not allowed. "
                "Explicitly define all fields."
            )
    
    def to_representation(self, instance):
        """Ensure all dates/decimals are properly formatted."""
        ret = super().to_representation(instance)
        
        # Convert Decimal fields to string for JSON compatibility
        for field_name, field_value in ret.items():
            if isinstance(field_value, Decimal):
                ret[field_name] = str(field_value)
        
        return ret

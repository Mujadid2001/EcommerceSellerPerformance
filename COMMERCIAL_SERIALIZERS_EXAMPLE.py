"""
Commercial-grade refactored serializers for performance module.

This file demonstrates the proper pattern for ALL serializers in the project:
- Explicit field definitions (NEVER use fields='__all__')
- Commercial-grade validators applied
- Proper error handling
- Consistent datetime/decimal formatting (ISO 8601 / string decimals)
- Type hints and docstrings

To apply these patterns:
1. Copy the patterns from this file
2. Update apps/performance/serializers.py
3. Update apps/authentication/serializers.py
4. Update all other app serializers
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional, Dict, Any

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import EmailValidator, MinValueValidator, MaxValueValidator

from apps.performance.models import Seller, Order, CustomerFeedback
from apps.core.serializer_validators import (
    StrictModelSerializer,
    DecimalValidator,
    MoneyValidator,
    PercentageValidator,
    RatingValidator,
    ISODateTimeValidator,
    ISODateValidator,
    DateNotInFutureValidator,
    CommercialEmailValidator,
    BusinessNameValidator,
    RegistrationNumberValidator,
    DateSequenceValidator,
    StatusTransitionValidator,
    FieldConverters,
)

User = get_user_model()


# ==================== SELLER SERIALIZERS ====================

class SellerMetricsReadOnlySerializer(serializers.Serializer):
    """Read-only serializer for seller performance metrics."""
    
    performance_score = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Performance score (0.00-100.00)'
    )
    total_orders = serializers.IntegerField(
        help_text='Total completed orders'
    )
    total_sales_volume = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Total sales amount'
    )
    average_delivery_days = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Average delivery time in days'
    )
    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[RatingValidator()],
        help_text='Average rating (1.00-5.00 stars)'
    )
    return_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[PercentageValidator()],
        help_text='Return rate percentage'
    )


class SellerListSerializer(StrictModelSerializer):
    """Optimized serializer for seller list view."""
    
    # Related field (denormalized for read-only)
    user_email = serializers.CharField(
        source='user.email',
        read_only=True,
        help_text='Associated user email'
    )
    
    # Status display
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
        help_text='Human-readable status'
    )
    
    # Explicit decimal fields with proper precision
    performance_score = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Seller performance score (0-100)'
    )
    
    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[RatingValidator()],
        help_text='Customer rating (1-5 stars)'
    )
    
    return_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[PercentageValidator()],
        help_text='Return rate percentage'
    )
    
    # Timestamps in ISO 8601
    created_at = serializers.DateTimeField(
        format='iso-8601',
        read_only=True,
        help_text='Account creation timestamp'
    )
    
    class Meta:
        model = Seller
        fields = [
            'id', 'user_email', 'business_name', 'status', 'status_display',
            'performance_score', 'average_rating', 'return_rate',
            'total_orders', 'total_sales_volume', 'created_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'status_display', 
            'performance_score', 'average_rating', 'return_rate',
            'total_orders', 'total_sales_volume', 'created_at'
        ]


class SellerDetailSerializer(StrictModelSerializer):
    """Serializer for seller detail view with full information."""
    
    # User details
    user_id = serializers.IntegerField(
        source='user.id',
        read_only=True,
        help_text='Associated user ID'
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True,
        help_text='Associated user email'
    )
    user_phone = serializers.CharField(
        source='user.phone',
        read_only=True,
        allow_null=True,
        help_text='User phone number'
    )
    
    # Status
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    # Metrics (explicit decimals with validators)
    performance_score = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Performance score (0-100)'
    )
    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[RatingValidator()],
        help_text='Customer rating (1-5 stars)'
    )
    return_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[PercentageValidator()],
        help_text='Return rate percentage'
    )
    average_delivery_days = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Average delivery days'
    )
    
    # Timestamps
    created_at = serializers.DateTimeField(
        format='iso-8601',
        read_only=True
    )
    updated_at = serializers.DateTimeField(
        format='iso-8601',
        read_only=True
    )
    status_updated_at = serializers.DateTimeField(
        format='iso-8601',
        read_only=True
    )
    last_evaluated_at = serializers.DateTimeField(
        format='iso-8601',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Seller
        fields = [
            'id', 'user_id', 'user_email', 'user_phone',
            'business_name', 'business_registration', 'description',
            'status', 'status_display',
            'performance_score', 'average_rating', 'return_rate',
            'average_delivery_days', 'total_orders', 'total_sales_volume',
            'created_at', 'updated_at', 'status_updated_at', 'last_evaluated_at'
        ]
        read_only_fields = [
            'id', 'user_id', 'user_email', 'user_phone', 'status_display',
            'performance_score', 'average_rating', 'return_rate',
            'average_delivery_days', 'total_orders', 'total_sales_volume',
            'created_at', 'updated_at', 'status_updated_at', 'last_evaluated_at'
        ]


# ==================== ORDER SERIALIZERS ====================

class OrderListSerializer(StrictModelSerializer):
    """Optimized serializer for order list view."""
    
    # Related fields
    seller_name = serializers.CharField(
        source='seller.business_name',
        read_only=True,
        help_text='Seller business name'
    )
    
    # Amount field - explicit decimal with validators
    order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MoneyValidator()],
        help_text='Order amount (currency)'
    )
    
    # Dates in ISO 8601
    order_date = serializers.DateTimeField(
        format='iso-8601',
        validators=[DateNotInFutureValidator(allow_today=True)],
        help_text='Order date in ISO 8601 format'
    )
    
    shipped_date = serializers.DateTimeField(
        format='iso-8601',
        required=False,
        allow_null=True,
        help_text='Ship date in ISO 8601 format'
    )
    
    delivered_date = serializers.DateTimeField(
        format='iso-8601',
        required=False,
        allow_null=True,
        help_text='Delivery date in ISO 8601 format'
    )
    
    # Status
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    # Calculated field
    delivery_days = serializers.IntegerField(
        read_only=True,
        help_text='Days from order to delivery'
    )
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'seller_name', 'customer_email',
            'order_amount', 'order_date', 'shipped_date', 'delivered_date',
            'status', 'status_display', 'delivery_days'
        ]
        read_only_fields = [
            'id', 'order_number', 'seller_name', 'status_display', 'delivery_days'
        ]


class OrderDetailSerializer(StrictModelSerializer):
    """Serializer for order detail view with full information."""
    
    # Seller details
    seller_id = serializers.IntegerField(
        source='seller.id',
        read_only=True
    )
    seller_name = serializers.CharField(
        source='seller.business_name',
        read_only=True
    )
    
    # Amount - strict decimal handling
    order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MoneyValidator()],
        help_text='Order total amount'
    )
    
    # Dates - ISO 8601 with validation
    order_date = serializers.DateTimeField(
        format='iso-8601',
        validators=[DateNotInFutureValidator(allow_today=True)]
    )
    shipped_date = serializers.DateTimeField(
        format='iso-8601',
        required=False,
        allow_null=True
    )
    delivered_date = serializers.DateTimeField(
        format='iso-8601',
        required=False,
        allow_null=True
    )
    
    # Status
    status = serializers.ChoiceField(
        choices=Order.Status.choices,
        help_text='Current order status'
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    # Return info
    is_returned = serializers.BooleanField(
        read_only=True
    )
    return_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text='Reason for return if applicable'
    )
    
    # Calculated fields
    delivery_days = serializers.IntegerField(
        read_only=True
    )
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'seller_id', 'seller_name',
            'customer_email', 'order_amount', 'order_date',
            'shipped_date', 'delivered_date', 'status', 'status_display',
            'is_returned', 'return_reason', 'delivery_days'
        ]
        read_only_fields = [
            'id', 'order_number', 'seller_id', 'seller_name',
            'status_display', 'is_returned', 'delivery_days'
        ]
    
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate date sequences and status transitions."""
        
        # If this is an update, check status transition validity
        if self.instance:
            current_status = self.instance.status
            new_status = attrs.get('status', current_status)
            
            # Define valid transitions
            valid_transitions = {
                'pending': ['processing', 'cancelled'],
                'processing': ['shipped', 'cancelled'],
                'shipped': ['delivered', 'returned'],
                'delivered': ['returned'],
                'cancelled': [],
                'returned': []
            }
            
            # Validate transition
            if current_status in valid_transitions:
                allowed = valid_transitions[current_status]
                if new_status not in allowed:
                    raise serializers.ValidationError({
                        'status': (
                            f"Cannot transition from {current_status} to {new_status}. "
                            f"Allowed: {', '.join(allowed)}"
                        )
                    })
        
        # Validate date sequences
        order_date = attrs.get('order_date', self.instance.order_date if self.instance else None)
        shipped_date = attrs.get('shipped_date', self.instance.shipped_date if self.instance else None)
        delivered_date = attrs.get('delivered_date', self.instance.delivered_date if self.instance else None)
        
        if shipped_date and order_date and shipped_date < order_date:
            raise serializers.ValidationError({
                'shipped_date': 'Shipped date must be after order date'
            })
        
        if delivered_date and shipped_date and delivered_date < shipped_date:
            raise serializers.ValidationError({
                'delivered_date': 'Delivered date must be after shipped date'
            })
        
        # Status-specific requirements
        new_status = attrs.get('status', self.instance.status if self.instance else None)
        
        if new_status == 'shipped' and not shipped_date:
            raise serializers.ValidationError({
                'shipped_date': 'Shipped date is required for shipped status'
            })
        
        if new_status == 'delivered' and not delivered_date:
            raise serializers.ValidationError({
                'delivered_date': 'Delivered date is required for delivered status'
            })
        
        if new_status == 'returned' and not attrs.get('return_reason'):
            raise serializers.ValidationError({
                'return_reason': 'Return reason is required for returned status'
            })
        
        return attrs


# ==================== CUSTOMER FEEDBACK SERIALIZERS ====================

class CustomerFeedbackSerializer(StrictModelSerializer):
    """Serializer for customer feedback with rating validation."""
    
    # Order info
    order_number = serializers.CharField(
        source='order.order_number',
        read_only=True
    )
    seller_name = serializers.CharField(
        source='order.seller.business_name',
        read_only=True
    )
    
    # Rating with commercial validator
    rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[RatingValidator()],
        help_text='Rating from 1.00 to 5.00 stars'
    )
    
    # Comment
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text='Customer feedback comment'
    )
    
    # Timestamp
    created_at = serializers.DateTimeField(
        format='iso-8601',
        read_only=True
    )
    
    class Meta:
        model = CustomerFeedback
        fields = [
            'id', 'order_number', 'seller_name', 'customer_email',
            'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'order_number', 'seller_name', 'created_at']


# ==================== IMPLEMENTATION GUIDE ====================

"""
HOW TO APPLY THESE PATTERNS:

1. EXPLICIT FIELDS (Never use '__all__')
   ✅ fields = ['id', 'name', 'email', ...]
   ❌ fields = '__all__'

2. DECIMAL FIELDS (Always use string in JSON)
   order_amount = serializers.DecimalField(
       max_digits=10,
       decimal_places=2,
       validators=[MoneyValidator()]  # Applied!
   )

3. DATETIME FIELDS (Always ISO 8601)
   order_date = serializers.DateTimeField(
       format='iso-8601',
       validators=[DateNotInFutureValidator()]
   )

4. CUSTOM VALIDATORS
   - MoneyValidator() for currency
   - PercentageValidator() for 0-100
   - RatingValidator() for 1-5 stars
   - DateNotInFutureValidator()
   - CommercialEmailValidator()
   - StatusTransitionValidator()
   - DateSequenceValidator()

5. READ-ONLY FIELDS
   Define relationships as denormalized read-only fields:
   user_email = serializers.CharField(
       source='user.email',
       read_only=True
   )

6. FIELD HELP TEXT
   Always add help_text for API documentation:
   order_amount = serializers.DecimalField(
       ...,
       help_text='Order total amount in decimal format'
   )

7. CONSISTENT FORMATTING
   - All monetary values: Decimal, 2 decimal places, string in JSON
   - All dates: ISO 8601 format ('2024-01-15T10:30:00+00:00')
   - All ratings: Decimal 1.00-5.00
   - All percentages: Decimal 0.00-100.00

8. VALIDATE IN VALIDATE() METHOD
   def validate(self, attrs):
       # Complex validations here
       return attrs
"""

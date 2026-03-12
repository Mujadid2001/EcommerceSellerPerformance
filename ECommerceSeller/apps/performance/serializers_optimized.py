"""
Optimized API Serializers for Performance app following industry best practices
"""
import uuid
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import EmailValidator, MinValueValidator
from datetime import timedelta

from apps.performance.models import Seller, Order, CustomerFeedback

User = get_user_model()


# ==================== BASE SERIALIZERS ====================

class BaseModelSerializer(serializers.ModelSerializer):
    """Base serializer with common functionality"""
    
    def validate_future_date(self, value, field_name="date"):
        """Validate that a date is not significantly in the future"""
        if value and value > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError(f"{field_name.title()} cannot be in the future.")
        return value


# ==================== USER SERIALIZERS ====================

class UserSerializer(serializers.ModelSerializer):
    """Optimized User serializer"""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone']
        read_only_fields = ['id', 'email']


# ==================== SELLER SERIALIZERS ====================

class SellerBaseSerializer(BaseModelSerializer):
    """Base seller serializer with common fields"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Seller
        fields = [
            'id', 'user_email', 'business_name', 'status', 'status_display',
            'performance_score', 'total_orders', 'total_sales_volume',
            'average_rating', 'return_rate', 'created_at'
        ]


class SellerListSerializer(SellerBaseSerializer):
    """Serializer for Seller list view - optimized for performance"""
    
    class Meta(SellerBaseSerializer.Meta):
        read_only_fields = SellerBaseSerializer.Meta.fields


class SellerDetailSerializer(SellerBaseSerializer):
    """Serializer for Seller detail view with full information"""
    user = UserSerializer(read_only=True)
    
    class Meta(SellerBaseSerializer.Meta):
        fields = SellerBaseSerializer.Meta.fields + [
            'user', 'business_registration', 'description',
            'average_delivery_days', 'updated_at',
            'status_updated_at', 'last_evaluated_at'
        ]


# ==================== ORDER SERIALIZERS ====================

class OrderBaseSerializer(BaseModelSerializer):
    """Base order serializer with common validation"""
    
    customer_email = serializers.EmailField(
        validators=[EmailValidator()],
        help_text="Valid email address of the customer"
    )
    order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Order amount must be greater than 0"
    )
    delivery_days = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_email', 'order_amount',
            'order_date', 'shipped_date', 'delivered_date', 'status',
            'return_reason', 'delivery_days'
        ]
        read_only_fields = ['id', 'order_number', 'delivery_days']

    def validate_customer_email(self, value):
        """Normalize and validate customer email"""
        return value.lower().strip()

    def validate_order_date(self, value):
        """Validate order date with tolerance for timezone issues"""
        return self.validate_future_date(value, "Order date")


class OrderListSerializer(OrderBaseSerializer):
    """Optimized serializer for order list view"""
    seller_name = serializers.CharField(source='seller.business_name', read_only=True)
    
    class Meta(OrderBaseSerializer.Meta):
        fields = [
            'id', 'order_number', 'customer_email', 'order_amount',
            'order_date', 'status', 'delivery_days', 'seller_name'
        ]


class OrderCreateSerializer(OrderBaseSerializer):
    """Serializer for creating new orders with validation"""
    
    class Meta(OrderBaseSerializer.Meta):
        fields = [
            'customer_email', 'order_amount', 'order_date', 
            'status'
        ]
        extra_kwargs = {
            'order_date': {'required': False},
        }

    def validate_status(self, value):
        """Validate initial status for new orders"""
        allowed_initial_statuses = ['pending', 'processing']
        if value not in allowed_initial_statuses:
            raise serializers.ValidationError(
                f"New orders can only be created with status: {', '.join(allowed_initial_statuses)}"
            )
        return value

    def create(self, validated_data):
        """Create order with auto-generated fields"""
        # Get seller from context
        seller = self._get_seller_from_context()
        
        # Generate unique order number
        order_number = self._generate_order_number(seller)
        
        # Set default order date if not provided
        if not validated_data.get('order_date'):
            validated_data['order_date'] = timezone.now()
            
        # Create and return order
        return Order.objects.create(
            seller=seller,
            order_number=order_number,
            **validated_data
        )

    def _get_seller_from_context(self):
        """Get seller from request context with validation"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated")
            
        try:
            return request.user.seller_profile
        except Seller.DoesNotExist:
            raise serializers.ValidationError("User must have a seller profile")

    def _generate_order_number(self, seller):
        """Generate unique order number with seller prefix"""
        prefix = f"ORD{seller.id}"
        unique_id = uuid.uuid4().hex[:8].upper()
        order_number = f"{prefix}{unique_id}"
        
        # Ensure uniqueness
        while Order.objects.filter(order_number=order_number).exists():
            unique_id = uuid.uuid4().hex[:8].upper()
            order_number = f"{prefix}{unique_id}"
        
        return order_number


class OrderUpdateSerializer(OrderBaseSerializer):
    """Serializer for updating orders with comprehensive validation"""
    
    class Meta(OrderBaseSerializer.Meta):
        fields = [
            'status', 'shipped_date', 'delivered_date', 'return_reason'
        ]
        extra_kwargs = {
            'shipped_date': {'required': False},
            'delivered_date': {'required': False}, 
            'return_reason': {'required': False},
        }

    def validate_shipped_date(self, value):
        """Validate shipped date"""
        return self.validate_future_date(value, "Shipped date")

    def validate_delivered_date(self, value):
        """Validate delivered date"""
        return self.validate_future_date(value, "Delivered date")

    def validate(self, attrs):
        """Comprehensive cross-field validation"""
        attrs = super().validate(attrs)
        
        # Get current and new values
        current_status = self.instance.status
        new_status = attrs.get('status', current_status)
        
        # Validate status transitions
        self._validate_status_transition(current_status, new_status)
        
        # Validate date relationships
        self._validate_date_relationships(attrs)
        
        # Status-specific validations
        self._validate_status_specific_requirements(attrs)
        
        return attrs

    def _validate_status_transition(self, current_status, new_status):
        """Validate allowed status transitions"""
        valid_transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'cancelled'],
            'delivered': ['returned'],  
            'cancelled': [],  # Terminal state
            'returned': []    # Terminal state
        }
        
        allowed = valid_transitions.get(current_status, [])
        if new_status != current_status and new_status not in allowed:
            raise serializers.ValidationError({
                'status': f'Cannot transition from {current_status} to {new_status}. '
                         f'Allowed transitions: {", ".join(allowed) if allowed else "None"}'
            })

    def _validate_date_relationships(self, attrs):
        """Validate date field relationships"""
        # Get current values from instance or new values
        order_date = self.instance.order_date
        shipped_date = attrs.get('shipped_date', self.instance.shipped_date)
        delivered_date = attrs.get('delivered_date', self.instance.delivered_date)
        
        # Validate shipped_date vs order_date
        if shipped_date and order_date and shipped_date < order_date:
            raise serializers.ValidationError({
                'shipped_date': 'Shipped date cannot be before order date'
            })
        
        # Validate delivered_date vs shipped_date
        if delivered_date and shipped_date and delivered_date < shipped_date:
            raise serializers.ValidationError({
                'delivered_date': 'Delivered date cannot be before shipped date'
            })
        
        # Validate delivered_date vs order_date
        if delivered_date and order_date and delivered_date < order_date:
            raise serializers.ValidationError({
                'delivered_date': 'Delivered date cannot be before order date'
            })

    def _validate_status_specific_requirements(self, attrs):
        """Validate status-specific field requirements"""
        new_status = attrs.get('status', self.instance.status)
        
        # Shipped status requires shipped_date
        if new_status == 'shipped':
            shipped_date = attrs.get('shipped_date', self.instance.shipped_date)
            if not shipped_date:
                raise serializers.ValidationError({
                    'shipped_date': 'Shipped date is required when status is shipped'
                })
        
        # Delivered status requires delivered_date
        if new_status == 'delivered':
            delivered_date = attrs.get('delivered_date', self.instance.delivered_date)
            if not delivered_date:
                raise serializers.ValidationError({
                    'delivered_date': 'Delivered date is required when status is delivered'
                })
        
        # Returned status requires return_reason
        if new_status == 'returned':
            return_reason = attrs.get('return_reason', self.instance.return_reason)
            if not return_reason or not return_reason.strip():
                raise serializers.ValidationError({
                    'return_reason': 'Return reason is required when status is returned'
                })


class OrderDetailSerializer(OrderBaseSerializer):
    """Detailed serializer for single order view"""
    seller_info = serializers.SerializerMethodField()
    
    class Meta(OrderBaseSerializer.Meta):
        fields = OrderBaseSerializer.Meta.fields + ['seller_info']

    def get_seller_info(self, obj):
        """Get seller information for the order"""
        return {
            'id': obj.seller.id,
            'business_name': obj.seller.business_name,
            'business_registration': obj.seller.business_registration,
            'performance_score': obj.seller.performance_score
        }


# ==================== CUSTOMER FEEDBACK SERIALIZERS ====================

class CustomerFeedbackSerializer(BaseModelSerializer):
    """Serializer for customer feedback"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    seller_name = serializers.CharField(source='order.seller.business_name', read_only=True)
    
    class Meta:
        model = CustomerFeedback
        fields = [
            'id', 'order', 'order_number', 'seller_name',
            'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'order_number', 'seller_name', 'created_at']

    def validate_rating(self, value):
        """Validate rating is within allowed range"""
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


# ==================== SERIALIZER REGISTRY ====================

class SerializerRegistry:
    """Registry for easy serializer access"""
    
    ORDER_SERIALIZERS = {
        'list': OrderListSerializer,
        'create': OrderCreateSerializer, 
        'update': OrderUpdateSerializer,
        'retrieve': OrderDetailSerializer,
        'default': OrderBaseSerializer
    }
    
    SELLER_SERIALIZERS = {
        'list': SellerListSerializer,
        'retrieve': SellerDetailSerializer,
        'default': SellerBaseSerializer
    }
    
    @classmethod
    def get_order_serializer(cls, action='default'):
        """Get order serializer by action"""
        return cls.ORDER_SERIALIZERS.get(action, cls.ORDER_SERIALIZERS['default'])
    
    @classmethod
    def get_seller_serializer(cls, action='default'):
        """Get seller serializer by action"""
        return cls.SELLER_SERIALIZERS.get(action, cls.SELLER_SERIALIZERS['default'])


# Export commonly used serializers and registry
__all__ = [
    'UserSerializer',
    'SellerListSerializer', 'SellerDetailSerializer',
    'OrderListSerializer', 'OrderCreateSerializer', 
    'OrderUpdateSerializer', 'OrderDetailSerializer',
    'CustomerFeedbackSerializer',
    'SerializerRegistry'
]
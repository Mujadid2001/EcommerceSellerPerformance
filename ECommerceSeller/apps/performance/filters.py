"""
Optimized Filters for Performance app
"""
import django_filters
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import Order, Seller, CustomerFeedback


class BaseFilterSet(django_filters.FilterSet):
    """Base filter with common functionality"""
    
    class Meta:
        abstract = True
    
    def filter_date_range(self, queryset, name, value):
        """Filter by date range in days"""
        try:
            days = int(value)
            if days > 0:
                start_date = timezone.now() - timedelta(days=days)
                return queryset.filter(**{f"{name}__gte": start_date})
        except (ValueError, TypeError):
            pass
        return queryset


class OrderFilter(BaseFilterSet):
    """Advanced filtering for orders"""
    
    # Date filters
    order_date = django_filters.DateFromToRangeFilter()
    order_date_range = django_filters.NumberFilter(
        method='filter_order_date_range',
        help_text='Filter orders from X days ago'
    )
    
    # Status filters
    status = django_filters.ChoiceFilter(choices=Order.STATUS_CHOICES)
    status_in = django_filters.ModelMultipleChoiceFilter(
        field_name='status',
        to_field_name='status',
        queryset=Order.objects.values_list('status', flat=True).distinct()
    )
    
    # Amount filters
    order_amount = django_filters.RangeFilter()
    order_amount_min = django_filters.NumberFilter(
        field_name='order_amount', lookup_expr='gte'
    )
    order_amount_max = django_filters.NumberFilter(
        field_name='order_amount', lookup_expr='lte'
    )
    
    # Return filter
    is_returned = django_filters.BooleanFilter(method='filter_is_returned')
    
    # Search filters
    search = django_filters.CharFilter(method='filter_search')
    customer = django_filters.CharFilter(
        field_name='customer_email', lookup_expr='icontains'
    )
    order_number = django_filters.CharFilter(lookup_expr='icontains')
    
    # Delivery filters
    delivery_days = django_filters.RangeFilter()
    is_delivered = django_filters.BooleanFilter(method='filter_is_delivered')
    
    class Meta:
        model = Order
        fields = {
            'status': ['exact', 'in'],
            'order_date': ['exact', 'gte', 'lte'],
            'order_amount': ['exact', 'gte', 'lte'],
            'customer_email': ['exact', 'icontains'],
            'order_number': ['exact', 'icontains'],
        }

    def filter_order_date_range(self, queryset, name, value):
        """Filter orders by date range in days"""
        return self.filter_date_range(queryset, 'order_date', value)

    def filter_is_returned(self, queryset, name, value):
        """Filter by return status"""
        if value is True:
            return queryset.filter(status='returned')
        elif value is False:
            return queryset.exclude(status='returned')
        return queryset

    def filter_is_delivered(self, queryset, name, value):
        """Filter by delivery status"""
        if value is True:
            return queryset.filter(status='delivered')
        elif value is False:
            return queryset.exclude(status='delivered')
        return queryset

    def filter_search(self, queryset, name, value):
        """Global search across multiple fields"""
        if value:
            return queryset.filter(
                Q(order_number__icontains=value) |
                Q(customer_email__icontains=value) |
                Q(status__icontains=value)
            )
        return queryset


class SellerFilter(BaseFilterSet):
    """Advanced filtering for sellers"""
    
    # Status filters
    status = django_filters.ChoiceFilter(choices=Seller.STATUS_CHOICES)
    is_active = django_filters.BooleanFilter(method='filter_is_active')
    
    # Performance filters
    performance_score = django_filters.RangeFilter()
    performance_score_min = django_filters.NumberFilter(
        field_name='performance_score', lookup_expr='gte'
    )
    performance_score_max = django_filters.NumberFilter(
        field_name='performance_score', lookup_expr='lte'
    )
    
    # Business filters
    business_name = django_filters.CharFilter(lookup_expr='icontains')
    has_business_registration = django_filters.BooleanFilter(
        method='filter_has_business_registration'
    )
    
    # Statistics filters
    total_orders = django_filters.RangeFilter()
    total_orders_min = django_filters.NumberFilter(
        field_name='total_orders', lookup_expr='gte'
    )
    
    average_rating = django_filters.RangeFilter()
    average_rating_min = django_filters.NumberFilter(
        field_name='average_rating', lookup_expr='gte'
    )
    
    return_rate = django_filters.RangeFilter()
    return_rate_max = django_filters.NumberFilter(
        field_name='return_rate', lookup_expr='lte'
    )
    
    # Date filters
    created_date = django_filters.DateFromToRangeFilter(field_name='created_at')
    created_range = django_filters.NumberFilter(
        method='filter_created_range',
        help_text='Filter sellers created X days ago'
    )
    
    class Meta:
        model = Seller
        fields = {
            'status': ['exact'],
            'business_name': ['exact', 'icontains'],
            'performance_score': ['exact', 'gte', 'lte'],
            'total_orders': ['exact', 'gte', 'lte'],
            'average_rating': ['exact', 'gte', 'lte'],
            'return_rate': ['exact', 'gte', 'lte'],
            'created_at': ['exact', 'gte', 'lte'],
        }

    def filter_is_active(self, queryset, name, value):
        """Filter by active status"""
        if value is True:
            return queryset.filter(status='active')
        elif value is False:
            return queryset.exclude(status='active')
        return queryset

    def filter_has_business_registration(self, queryset, name, value):
        """Filter by business registration presence"""
        if value is True:
            return queryset.exclude(business_registration__isnull=True).exclude(business_registration='')
        elif value is False:
            return queryset.filter(Q(business_registration__isnull=True) | Q(business_registration=''))
        return queryset

    def filter_created_range(self, queryset, name, value):
        """Filter sellers by creation date range in days"""
        return self.filter_date_range(queryset, 'created_at', value)


class CustomerFeedbackFilter(BaseFilterSet):
    """Advanced filtering for customer feedback"""
    
    # Rating filters
    rating = django_filters.ChoiceFilter(choices=[(i, i) for i in range(1, 6)])
    rating_min = django_filters.NumberFilter(
        field_name='rating', lookup_expr='gte'
    )
    rating_max = django_filters.NumberFilter(
        field_name='rating', lookup_expr='lte'
    )
    rating_range = django_filters.RangeFilter(field_name='rating')
    
    # High/low rating filters
    is_positive = django_filters.BooleanFilter(method='filter_is_positive')
    is_negative = django_filters.BooleanFilter(method='filter_is_negative')
    
    # Order filters
    order_status = django_filters.CharFilter(field_name='order__status')
    order_number = django_filters.CharFilter(
        field_name='order__order_number', lookup_expr='icontains'
    )
    
    # Content filters
    has_comment = django_filters.BooleanFilter(method='filter_has_comment')
    comment = django_filters.CharFilter(lookup_expr='icontains')
    
    # Date filters
    created_date = django_filters.DateFromToRangeFilter(field_name='created_at')
    created_range = django_filters.NumberFilter(
        method='filter_created_range',
        help_text='Filter feedback from X days ago'
    )
    
    class Meta:
        model = CustomerFeedback
        fields = {
            'rating': ['exact', 'gte', 'lte'],
            'comment': ['icontains'],
            'created_at': ['exact', 'gte', 'lte'],
            'order__status': ['exact'],
            'order__order_number': ['exact', 'icontains'],
        }

    def filter_is_positive(self, queryset, name, value):
        """Filter positive feedback (rating >= 4)"""
        if value is True:
            return queryset.filter(rating__gte=4)
        elif value is False:
            return queryset.filter(rating__lt=4)
        return queryset

    def filter_is_negative(self, queryset, name, value):
        """Filter negative feedback (rating <= 2)"""
        if value is True:
            return queryset.filter(rating__lte=2)
        elif value is False:
            return queryset.filter(rating__gt=2)
        return queryset

    def filter_has_comment(self, queryset, name, value):
        """Filter feedback with/without comments"""
        if value is True:
            return queryset.exclude(comment__isnull=True).exclude(comment='')
        elif value is False:
            return queryset.filter(Q(comment__isnull=True) | Q(comment=''))
        return queryset

    def filter_created_range(self, queryset, name, value):
        """Filter feedback by creation date range in days"""
        return self.filter_date_range(queryset, 'created_at', value)


# ==================== CUSTOM FILTER BACKENDS ====================

class AdvancedSearchFilter(django_filters.rest_framework.DjangoFilterBackend):
    """
    Enhanced search filter with advanced features
    """
    
    def get_filterset_kwargs(self, request, queryset, view):
        """Add custom filter kwargs"""
        kwargs = super().get_filterset_kwargs(request, queryset, view)
        
        # Add request to filterset for context-aware filtering
        if kwargs.get('data') is not None:
            kwargs['request'] = request
            
        return kwargs


# ==================== FILTER UTILITIES ====================

class FilterUtils:
    """Utility class for filter-related operations"""
    
    @staticmethod
    def get_filter_choices(model, field):
        """Get distinct choices for a model field"""
        return model.objects.values_list(field, flat=True).distinct().order_by(field)
    
    @staticmethod
    def build_date_filter(days):
        """Build date filter for X days ago"""
        if days:
            try:
                days = int(days)
                return timezone.now() - timedelta(days=days)
            except (ValueError, TypeError):
                pass
        return None
    
    @staticmethod
    def build_search_query(search_term, fields):
        """Build Q object for searching multiple fields"""
        if not search_term:
            return Q()
        
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": search_term})
        
        return query


# ==================== EXPORTS ====================

__all__ = [
    'OrderFilter',
    'SellerFilter', 
    'CustomerFeedbackFilter',
    'AdvancedSearchFilter',
    'FilterUtils'
]
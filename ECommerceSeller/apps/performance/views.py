"""
Optimized Views for Performance app following industry best practices
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# from django_filters.rest_framework import DjangoFilterBackend  # TODO: Install django-filter
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.utils import timezone
from datetime import timedelta

from .models import Order, Seller, CustomerFeedback
from .serializers import (
    SerializerRegistry, CustomerFeedbackSerializer, 
    OrderListSerializer, OrderCreateSerializer, OrderUpdateSerializer, OrderDetailSerializer,
    SellerListSerializer, SellerDetailSerializer
)
# from .filters import OrderFilter  # TODO: Install django-filter
# from .permissions import IsSellerOwner  # TODO: Create permissions
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse


# ==================== BASE VIEWSET ====================

class OptimizedBaseViewSet(viewsets.ModelViewSet):
    """Base viewset with common optimizations and patterns"""
    
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]  # TODO: Add DjangoFilterBackend when django-filter is installed
    
    def get_serializer_class(self):
        """Get appropriate serializer based on action"""
        return self.serializer_classes.get(
            self.action,
            self.serializer_classes.get('default', super().get_serializer_class())
        )
    
    def get_queryset(self):
        """Override to add common optimizations"""
        queryset = super().get_queryset()
        return self.optimize_queryset(queryset)
    
    def optimize_queryset(self, queryset):
        """Hook for subclasses to add query optimizations"""
        return queryset
    
    def handle_exception(self, exc):
        """Enhanced exception handling with logging"""
        # Log error for monitoring
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in {self.__class__.__name__}: {exc}", exc_info=True)
        
        return super().handle_exception(exc)


# ==================== ORDER VIEWSET ====================

@method_decorator(login_required, name='dispatch')
class OrderViewSet(OptimizedBaseViewSet):
    """
    Optimized ViewSet for Order management with comprehensive features
    """
    
    # Serializer configuration
    serializer_classes = {
        'list': OrderListSerializer,
        'create': OrderCreateSerializer,
        'update': OrderUpdateSerializer,
        'partial_update': OrderUpdateSerializer,
        'retrieve': OrderDetailSerializer,
        'default': OrderListSerializer
    }
    
    # Filter configuration
    # filterset_class = OrderFilter  # TODO: Install django-filter
    search_fields = ['order_number', 'customer_email', 'status']
    ordering_fields = ['order_date', 'order_amount', 'status', 'delivery_days']
    ordering = ['-order_date']  # Default ordering
    
    # Pagination
    pagination_class = None  # Use default from settings
    
    def get_queryset(self):
        """Get orders for current seller with optimizations"""
        if not hasattr(self.request.user, 'seller_profile'):
            return Order.objects.none()
        
        return self.optimize_queryset(
            Order.objects.filter(seller=self.request.user.seller_profile)
        )
    
    def optimize_queryset(self, queryset):
        """Add query optimizations"""
        return queryset.select_related('seller').prefetch_related(
            Prefetch('seller', queryset=Seller.objects.select_related('user'))
        )
    
    def perform_create(self, serializer):
        """Create order with seller context"""
        # Serializer handles seller assignment via context
        serializer.save()
    
    def perform_update(self, serializer):
        """Update order with validation"""
        serializer.save()
    
    # ==================== CUSTOM ACTIONS ====================
    
    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """
        Enhanced endpoint for seller's orders with filtering and pagination
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply additional filters from query params
        queryset = self._apply_custom_filters(queryset, request)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def statistics(self, request):
        """
        Get order statistics for current seller
        """
        queryset = self.get_queryset()
        
        stats = {
            'total_orders': queryset.count(),
            'pending_orders': queryset.filter(status='pending').count(),
            'processing_orders': queryset.filter(status='processing').count(),
            'shipped_orders': queryset.filter(status='shipped').count(),
            'delivered_orders': queryset.filter(status='delivered').count(),
            'cancelled_orders': queryset.filter(status='cancelled').count(),
            'returned_orders': queryset.filter(status='returned').count(),
            'total_revenue': float(queryset.aggregate(
                total=models.Sum('order_amount')
            )['total'] or 0),
            'average_order_value': float(queryset.aggregate(
                avg=models.Avg('order_amount')
            )['avg'] or 0),
        }
        
        # Recent orders (last 30 days)
        recent_date = timezone.now() - timedelta(days=30)
        recent_orders = queryset.filter(order_date__gte=recent_date)
        stats['recent_orders'] = recent_orders.count()
        stats['recent_revenue'] = float(recent_orders.aggregate(
            total=models.Sum('order_amount')
        )['total'] or 0)
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def mark_shipped(self, request, pk=None):
        """
        Quick action to mark order as shipped
        """
        order = self.get_object()
        
        if order.status not in ['pending', 'processing']:
            return Response(
                {'error': 'Order cannot be marked as shipped from current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(
            order,
            data={
                'status': 'shipped',
                'shipped_date': timezone.now()
            },
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        """
        Quick action to mark order as delivered
        """
        order = self.get_object()
        
        if order.status != 'shipped':
            return Response(
                {'error': 'Order must be shipped before marking as delivered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        delivered_date = request.data.get('delivered_date', timezone.now())
        
        serializer = self.get_serializer(
            order,
            data={
                'status': 'delivered',
                'delivered_date': delivered_date
            },
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # ==================== HELPER METHODS ====================
    
    def _apply_custom_filters(self, queryset, request):
        """Apply custom filters from query parameters"""
        # Date range filter
        days = request.query_params.get('days')
        if days:
            try:
                days = int(days)
                start_date = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(order_date__gte=start_date)
            except (ValueError, TypeError):
                pass  # Ignore invalid days parameter
        
        # Status filter
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Return filter
        is_returned = request.query_params.get('is_returned')
        if is_returned is not None:
            if is_returned.lower() == 'true':
                queryset = queryset.filter(status='returned')
            elif is_returned.lower() == 'false':
                queryset = queryset.exclude(status='returned')
        
        # Search filter
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(customer_email__icontains=search)
            )
        
        return queryset


# ==================== SELLER VIEWSET ====================

@method_decorator(login_required, name='dispatch')
class SellerViewSet(OptimizedBaseViewSet):
    """
    Optimized ViewSet for Seller management
    """
    
    permission_classes = [IsAuthenticated]  # TODO: Add IsSellerOwner when permissions are created
    
    # Serializer configuration
    serializer_classes = {
        'list': SellerListSerializer,
        'retrieve': SellerDetailSerializer,
        'default': SellerListSerializer
    }
    
    # Filter configuration
    search_fields = ['business_name', 'user__email']
    ordering_fields = ['business_name', 'performance_score', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get sellers with optimizations"""
        return self.optimize_queryset(Seller.objects.all())
    
    def optimize_queryset(self, queryset):
        """Add query optimizations"""
        return queryset.select_related('user').prefetch_related('orders')
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """
        Get current user's seller profile
        """
        try:
            seller = request.user.seller_profile
            serializer = self.get_serializer(seller)
            return Response(serializer.data)
        except Seller.DoesNotExist:
            return Response(
                {'error': 'Seller profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ==================== CUSTOMER FEEDBACK VIEWSET ====================

@method_decorator(login_required, name='dispatch')
class CustomerFeedbackViewSet(OptimizedBaseViewSet):
    """
    ViewSet for Customer Feedback management
    """
    
    from .serializers import CustomerFeedbackSerializer
    serializer_class = CustomerFeedbackSerializer
    filter_backends = [filters.OrderingFilter]  # TODO: Add DjangoFilterBackend when django-filter is installed
    ordering_fields = ['rating', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get feedback for current seller's orders"""
        if not hasattr(self.request.user, 'seller_profile'):
            return CustomerFeedback.objects.none()
        
        return CustomerFeedback.objects.filter(
            order__seller=self.request.user.seller_profile
        ).select_related('order', 'order__seller')
    
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 10))  # Cache for 10 minutes
    def summary(self, request):
        """
        Get feedback summary statistics
        """
        queryset = self.get_queryset()
        
        from django.db.models import Avg, Count
        
        summary = queryset.aggregate(
            total_reviews=Count('id'),
            average_rating=Avg('rating'),
            five_star=Count('id', filter=Q(rating=5)),
            four_star=Count('id', filter=Q(rating=4)),
            three_star=Count('id', filter=Q(rating=3)),
            two_star=Count('id', filter=Q(rating=2)),
            one_star=Count('id', filter=Q(rating=1)),
        )
        
        # Add percentages
        total = summary['total_reviews']
        if total > 0:
            for key in ['five_star', 'four_star', 'three_star', 'two_star', 'one_star']:
                summary[f"{key}_percent"] = round((summary[key] / total) * 100, 1)
        
        return Response(summary)


# ==================== ADDITIONAL UTILITY VIEWS ====================

class HealthCheckView(viewsets.ViewSet):
    """
    Simple health check endpoint for monitoring
    """
    permission_classes = []  # Public endpoint
    
    def list(self, request):
        """Health check endpoint"""
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0'
        })


# ==================== FUNCTION-BASED VIEWS ====================

@login_required
def marketplace_view(request):
    """Main marketplace view showing sellers"""
    sellers = Seller.objects.filter(status='active').select_related('user')[:20]
    context = {
        'sellers': sellers,
        'page_title': 'Marketplace'
    }
    return render(request, 'performance/marketplace.html', context)


@login_required
def seller_dashboard(request):
    """Seller dashboard view"""
    try:
        seller = request.user.seller_profile
        recent_orders = Order.objects.filter(seller=seller).order_by('-order_date')[:10]
        
        context = {
            'seller': seller,
            'recent_orders': recent_orders,
            'page_title': 'Dashboard'
        }
        return render(request, 'performance/dashboard.html', context)
    except Seller.DoesNotExist:
        return render(request, 'performance/no_seller_profile.html')


def seller_public_profile(request, seller_id):
    """Public seller profile view"""
    seller = get_object_or_404(Seller, id=seller_id, status='active')
    
    context = {
        'seller': seller,
        'page_title': f'{seller.business_name} - Profile'
    }
    return render(request, 'performance/seller_profile.html', context)


@login_required
def orders_view(request):
    """Orders management view"""
    context = {
        'page_title': 'Orders Management'
    }
    return render(request, 'performance/orders.html', context)


@login_required
def profile_view(request):
    """User profile view"""
    try:
        seller = request.user.seller_profile
        context = {
            'seller': seller,
            'page_title': 'Profile'
        }
        return render(request, 'performance/profile.html', context)
    except Seller.DoesNotExist:
        return render(request, 'performance/no_seller_profile.html')


# ==================== EXPORTS ====================

__all__ = [
    'OrderViewSet',
    'SellerViewSet', 
    'CustomerFeedbackViewSet',
    'HealthCheckView',
    'marketplace_view',
    'seller_dashboard',
    'seller_public_profile', 
    'orders_view',
    'profile_view'
]
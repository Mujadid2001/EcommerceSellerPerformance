"""
Custom manager and queryset for Order model
"""
from django.db import models
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone
from decimal import Decimal


class OrderQuerySet(models.QuerySet):
    """Custom queryset for Order model with optimized queries."""
    
    def for_seller(self, seller):
        """Filter orders for a specific seller."""
        return self.filter(seller=seller)
    
    def completed(self):
        """Filter successfully completed orders (delivered and not returned)."""
        return self.filter(status='delivered', is_returned=False)
    
    def returned(self):
        """Filter returned orders."""
        return self.filter(is_returned=True)
    
    def delivered(self):
        """Filter delivered orders."""
        return self.filter(status='delivered')
    
    def pending(self):
        """Filter pending orders."""
        return self.filter(status='pending')
    
    def with_seller_info(self):
        """Optimize queries by selecting related seller information."""
        return self.select_related('seller', 'seller__user')
    
    def with_feedback(self):
        """Include related feedback."""
        return self.select_related('feedback')
    
    def calculate_metrics_for_seller(self, seller):
        """
        Calculate comprehensive order metrics for a seller.
        Returns a dictionary with all computed metrics as Decimal for consistency.
        """
        orders = self.for_seller(seller)
        completed_orders = orders.completed()
        
        # Get aggregated values
        total_sales = completed_orders.aggregate(
            total=Sum('order_amount')
        )['total']
        
        avg_delivery = orders.filter(
            delivery_days__isnull=False
        ).aggregate(
            avg=Avg('delivery_days')
        )['avg']
        
        metrics = {
            'total_orders': orders.count(),
            'completed_orders': completed_orders.count(),
            'returned_orders': orders.returned().count(),
            'total_sales_volume': Decimal(str(total_sales)) if total_sales else Decimal('0.00'),
            'average_delivery_days': Decimal(str(avg_delivery)) if avg_delivery else Decimal('0.00'),
        }
        
        # Calculate return rate
        if metrics['total_orders'] > 0:
            metrics['return_rate'] = (
                Decimal(metrics['returned_orders']) / Decimal(metrics['total_orders'])
            ) * Decimal('100.00')
        else:
            metrics['return_rate'] = Decimal('0.00')
        
        return metrics
    
    def recent(self, days=30):
        """Filter orders from the last N days."""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(order_date__gte=cutoff_date)
    
    def by_status_counts(self):
        """Return count of orders grouped by status."""
        return self.values('status').annotate(count=Count('id')).order_by('status')


class OrderManager(models.Manager):
    """Custom manager for Order model."""
    
    def get_queryset(self):
        """Return custom queryset."""
        return OrderQuerySet(self.model, using=self._db)
    
    def for_seller(self, seller):
        """Get orders for a specific seller."""
        return self.get_queryset().for_seller(seller)
    
    def completed(self):
        """Get completed orders."""
        return self.get_queryset().completed()
    
    def returned(self):
        """Get returned orders."""
        return self.get_queryset().returned()
    
    def delivered(self):
        """Get delivered orders."""
        return self.get_queryset().delivered()
    
    def pending(self):
        """Get pending orders."""
        return self.get_queryset().pending()
    
    def with_seller_info(self):
        """Get orders with seller information."""
        return self.get_queryset().with_seller_info()
    
    def with_feedback(self):
        """Get orders with feedback."""
        return self.get_queryset().with_feedback()
    
    def calculate_metrics_for_seller(self, seller):
        """Calculate order metrics for a seller."""
        return self.get_queryset().calculate_metrics_for_seller(seller)
    
    def recent(self, days=30):
        """Get recent orders."""
        return self.get_queryset().recent(days)
    
    def by_status_counts(self):
        """Get order counts by status."""
        return self.get_queryset().by_status_counts()

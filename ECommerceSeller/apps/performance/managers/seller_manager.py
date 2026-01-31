"""
Custom manager and queryset for Seller model
"""
from django.db import models
from django.db.models import Avg, Count, Sum, Q, F
from decimal import Decimal


class SellerQuerySet(models.QuerySet):
    """Custom queryset for Seller model with performance-optimized queries."""
    
    def active(self):
        """Filter sellers with active status."""
        return self.filter(status='active')
    
    def under_review(self):
        """Filter sellers under review."""
        return self.filter(status='under_review')
    
    def suspended(self):
        """Filter suspended sellers."""
        return self.filter(status='suspended')
    
    def with_user_info(self):
        """Optimize queries by selecting related user information."""
        return self.select_related('user')
    
    def with_order_counts(self):
        """Annotate with order statistics."""
        return self.annotate(
            completed_orders_count=Count(
                'orders',
                filter=Q(orders__status='delivered', orders__is_returned=False)
            ),
            returned_orders_count=Count(
                'orders',
                filter=Q(orders__is_returned=True)
            ),
            total_orders_count=Count('orders')
        )
    
    def with_performance_metrics(self):
        """Annotate with computed performance metrics."""
        return self.annotate(
            computed_sales_volume=Sum(
                'orders__order_amount',
                filter=Q(orders__status='delivered', orders__is_returned=False)
            ),
            computed_avg_delivery=Avg(
                'orders__delivery_days',
                filter=Q(orders__status='delivered', orders__delivery_days__isnull=False)
            ),
            computed_avg_rating=Avg('feedbacks__rating'),
            feedback_count=Count('feedbacks')
        )
    
    def high_performers(self, threshold=Decimal('80.00')):
        """Filter sellers with high performance scores."""
        return self.filter(performance_score__gte=threshold)
    
    def low_performers(self, threshold=Decimal('50.00')):
        """Filter sellers with low performance scores."""
        return self.filter(performance_score__lt=threshold)
    
    def needs_evaluation(self):
        """
        Find sellers that need performance re-evaluation.
        Returns sellers who haven't been evaluated recently or never evaluated.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=7)
        return self.filter(
            Q(last_evaluated_at__isnull=True) | Q(last_evaluated_at__lt=cutoff_date)
        )
    
    def by_status_counts(self):
        """Return count of sellers grouped by status."""
        return self.values('status').annotate(count=Count('id')).order_by('status')


class SellerManager(models.Manager):
    """Custom manager for Seller model."""
    
    def get_queryset(self):
        """Return custom queryset."""
        return SellerQuerySet(self.model, using=self._db)
    
    def active(self):
        """Get active sellers."""
        return self.get_queryset().active()
    
    def under_review(self):
        """Get sellers under review."""
        return self.get_queryset().under_review()
    
    def suspended(self):
        """Get suspended sellers."""
        return self.get_queryset().suspended()
    
    def with_user_info(self):
        """Get sellers with user information."""
        return self.get_queryset().with_user_info()
    
    def with_order_counts(self):
        """Get sellers with order counts."""
        return self.get_queryset().with_order_counts()
    
    def with_performance_metrics(self):
        """Get sellers with performance metrics."""
        return self.get_queryset().with_performance_metrics()
    
    def high_performers(self, threshold=Decimal('80.00')):
        """Get high performing sellers."""
        return self.get_queryset().high_performers(threshold)
    
    def low_performers(self, threshold=Decimal('50.00')):
        """Get low performing sellers."""
        return self.get_queryset().low_performers(threshold)
    
    def needs_evaluation(self):
        """Get sellers needing evaluation."""
        return self.get_queryset().needs_evaluation()
    
    def by_status_counts(self):
        """Get seller counts by status."""
        return self.get_queryset().by_status_counts()

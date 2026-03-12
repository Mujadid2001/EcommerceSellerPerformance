"""
Performance Calculation Service

Implements weighted scoring algorithm for seller performance evaluation.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone


class PerformanceCalculationService:
    """
    Service for calculating seller performance scores using weighted metrics.
    
    Scoring Algorithm:
    - Sales Volume Weight: 30%
    - Delivery Speed Weight: 25%
    - Average Rating Weight: 30%
    - Returns Penalty: 15%
    
    Score Range: 0-100
    """
    
    # Configurable weights (must sum to 100)
    SALES_VOLUME_WEIGHT = Decimal('30.00')
    DELIVERY_SPEED_WEIGHT = Decimal('25.00')
    RATING_WEIGHT = Decimal('30.00')
    RETURNS_WEIGHT = Decimal('15.00')
    
    # Performance thresholds
    EXCELLENT_SALES_THRESHOLD = Decimal('100000.00')  # $100,000
    GOOD_SALES_THRESHOLD = Decimal('50000.00')  # $50,000
    
    EXCELLENT_DELIVERY_DAYS = Decimal('2.00')  # 2 days
    GOOD_DELIVERY_DAYS = Decimal('5.00')  # 5 days
    MAX_DELIVERY_DAYS = Decimal('14.00')  # 14 days
    
    EXCELLENT_RETURN_RATE = Decimal('2.00')  # 2%
    ACCEPTABLE_RETURN_RATE = Decimal('5.00')  # 5%
    MAX_RETURN_RATE = Decimal('20.00')  # 20%
    
    def __init__(self, seller):
        """
        Initialize service with a seller instance.
        
        Args:
            seller: Seller model instance
        """
        self.seller = seller
        self.metrics = {}
        self.score_breakdown = {}
    
    def calculate_performance_score(self) -> Decimal:
        """
        Calculate overall performance score for the seller.
        
        Returns:
            Decimal: Performance score between 0.00 and 100.00
        """
        # Gather metrics
        self._gather_metrics()
        
        # Calculate individual component scores
        sales_score = self._calculate_sales_score()
        delivery_score = self._calculate_delivery_score()
        rating_score = self._calculate_rating_score()
        returns_penalty = self._calculate_returns_penalty()
        
        # Calculate weighted total
        total_score = (
            (sales_score * self.SALES_VOLUME_WEIGHT / Decimal('100.00')) +
            (delivery_score * self.DELIVERY_SPEED_WEIGHT / Decimal('100.00')) +
            (rating_score * self.RATING_WEIGHT / Decimal('100.00')) +
            (returns_penalty * self.RETURNS_WEIGHT / Decimal('100.00'))
        )
        
        # Store breakdown for debugging/reporting
        self.score_breakdown = {
            'sales_score': sales_score,
            'delivery_score': delivery_score,
            'rating_score': rating_score,
            'returns_penalty': returns_penalty,
            'total_score': total_score,
            'weights': {
                'sales': self.SALES_VOLUME_WEIGHT,
                'delivery': self.DELIVERY_SPEED_WEIGHT,
                'rating': self.RATING_WEIGHT,
                'returns': self.RETURNS_WEIGHT,
            }
        }
        
        # Ensure score is within valid range
        final_score = max(Decimal('0.00'), min(Decimal('100.00'), total_score))
        
        return final_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def _gather_metrics(self) -> None:
        """Collect all necessary metrics from database."""
        from apps.performance.models import Order, CustomerFeedback
        
        # Get order metrics using manager
        order_metrics = Order.objects.calculate_metrics_for_seller(self.seller)
        
        # Get feedback metrics
        feedback_stats = CustomerFeedback.objects.filter(
            seller=self.seller
        ).aggregate(
            avg_rating=Avg('rating'),
            feedback_count=Count('id')
        )
        
        # Convert all values to Decimal for consistent arithmetic
        self.metrics = {
            'total_orders': order_metrics['total_orders'],
            'completed_orders': order_metrics['completed_orders'],
            'returned_orders': order_metrics['returned_orders'],
            'total_sales_volume': Decimal(str(order_metrics['total_sales_volume'])) if order_metrics['total_sales_volume'] else Decimal('0.00'),
            'average_delivery_days': Decimal(str(order_metrics['average_delivery_days'])) if order_metrics['average_delivery_days'] else Decimal('0.00'),
            'return_rate': Decimal(str(order_metrics['return_rate'])) if order_metrics['return_rate'] else Decimal('0.00'),
            'average_rating': Decimal(str(feedback_stats['avg_rating'])) if feedback_stats['avg_rating'] else Decimal('0.00'),
            'feedback_count': feedback_stats['feedback_count'] or 0,
        }
    
    def _calculate_sales_score(self) -> Decimal:
        """
        Calculate sales volume score (0-100).
        
        Logic:
        - >= $100k: 100 points
        - $50k-$100k: 70-100 points (linear)
        - $10k-$50k: 40-70 points (linear)
        - < $10k: 0-40 points (linear)
        """
        sales_volume = self.metrics['total_sales_volume']
        
        if sales_volume >= self.EXCELLENT_SALES_THRESHOLD:
            return Decimal('100.00')
        elif sales_volume >= self.GOOD_SALES_THRESHOLD:
            # Linear interpolation between 70 and 100
            ratio = (sales_volume - self.GOOD_SALES_THRESHOLD) / (
                self.EXCELLENT_SALES_THRESHOLD - self.GOOD_SALES_THRESHOLD
            )
            return Decimal('70.00') + (ratio * Decimal('30.00'))
        elif sales_volume >= Decimal('10000.00'):
            # Linear interpolation between 40 and 70
            ratio = (sales_volume - Decimal('10000.00')) / (
                self.GOOD_SALES_THRESHOLD - Decimal('10000.00')
            )
            return Decimal('40.00') + (ratio * Decimal('30.00'))
        else:
            # Linear interpolation between 0 and 40
            if sales_volume <= Decimal('0.00'):
                return Decimal('0.00')
            ratio = sales_volume / Decimal('10000.00')
            return ratio * Decimal('40.00')
    
    def _calculate_delivery_score(self) -> Decimal:
        """
        Calculate delivery speed score (0-100).
        
        Logic:
        - <= 2 days: 100 points
        - 2-5 days: 70-100 points (linear)
        - 5-10 days: 40-70 points (linear)
        - 10-14 days: 20-40 points (linear)
        - > 14 days: 0-20 points
        """
        avg_delivery = self.metrics['average_delivery_days']
        
        # Handle no delivery data
        if avg_delivery <= Decimal('0.00') or self.metrics['completed_orders'] == 0:
            return Decimal('50.00')  # Neutral score for new sellers
        
        if avg_delivery <= self.EXCELLENT_DELIVERY_DAYS:
            return Decimal('100.00')
        elif avg_delivery <= self.GOOD_DELIVERY_DAYS:
            # Linear interpolation between 70 and 100
            ratio = (avg_delivery - self.EXCELLENT_DELIVERY_DAYS) / (
                self.GOOD_DELIVERY_DAYS - self.EXCELLENT_DELIVERY_DAYS
            )
            return Decimal('100.00') - (ratio * Decimal('30.00'))
        elif avg_delivery <= Decimal('10.00'):
            # Linear interpolation between 40 and 70
            ratio = (avg_delivery - self.GOOD_DELIVERY_DAYS) / (
                Decimal('10.00') - self.GOOD_DELIVERY_DAYS
            )
            return Decimal('70.00') - (ratio * Decimal('30.00'))
        elif avg_delivery <= self.MAX_DELIVERY_DAYS:
            # Linear interpolation between 20 and 40
            ratio = (avg_delivery - Decimal('10.00')) / (
                self.MAX_DELIVERY_DAYS - Decimal('10.00')
            )
            return Decimal('40.00') - (ratio * Decimal('20.00'))
        else:
            # Very slow delivery
            penalty = min((avg_delivery - self.MAX_DELIVERY_DAYS) * Decimal('2.00'), Decimal('20.00'))
            return max(Decimal('0.00'), Decimal('20.00') - penalty)
    
    def _calculate_rating_score(self) -> Decimal:
        """
        Calculate customer rating score (0-100).
        
        Logic:
        - Rating is 1-5 stars, convert to 0-100 scale
        - No ratings: 50 points (neutral for new sellers)
        """
        avg_rating = self.metrics['average_rating']
        feedback_count = self.metrics['feedback_count']
        
        # Handle no ratings
        if feedback_count == 0 or avg_rating <= Decimal('0.00'):
            return Decimal('50.00')  # Neutral score for new sellers
        
        # Convert 1-5 scale to 0-100 scale
        # 5 stars = 100, 4 stars = 75, 3 stars = 50, 2 stars = 25, 1 star = 0
        score = ((avg_rating - Decimal('1.00')) / Decimal('4.00')) * Decimal('100.00')
        
        return score
    
    def _calculate_returns_penalty(self) -> Decimal:
        """
        Calculate returns penalty score (0-100).
        
        Logic:
        - Lower return rate = higher score
        - <= 2%: 100 points
        - 2-5%: 80-100 points (linear)
        - 5-10%: 50-80 points (linear)
        - 10-20%: 20-50 points (linear)
        - > 20%: 0-20 points
        """
        return_rate = self.metrics['return_rate']
        
        # Handle no orders
        if self.metrics['total_orders'] == 0:
            return Decimal('100.00')  # No penalty for new sellers
        
        if return_rate <= self.EXCELLENT_RETURN_RATE:
            return Decimal('100.00')
        elif return_rate <= self.ACCEPTABLE_RETURN_RATE:
            # Linear interpolation between 80 and 100
            ratio = (return_rate - self.EXCELLENT_RETURN_RATE) / (
                self.ACCEPTABLE_RETURN_RATE - self.EXCELLENT_RETURN_RATE
            )
            return Decimal('100.00') - (ratio * Decimal('20.00'))
        elif return_rate <= Decimal('10.00'):
            # Linear interpolation between 50 and 80
            ratio = (return_rate - self.ACCEPTABLE_RETURN_RATE) / (
                Decimal('10.00') - self.ACCEPTABLE_RETURN_RATE
            )
            return Decimal('80.00') - (ratio * Decimal('30.00'))
        elif return_rate <= self.MAX_RETURN_RATE:
            # Linear interpolation between 20 and 50
            ratio = (return_rate - Decimal('10.00')) / (
                self.MAX_RETURN_RATE - Decimal('10.00')
            )
            return Decimal('50.00') - (ratio * Decimal('30.00'))
        else:
            # Very high return rate
            penalty = min((return_rate - self.MAX_RETURN_RATE) * Decimal('2.00'), Decimal('20.00'))
            return max(Decimal('0.00'), Decimal('20.00') - penalty)
    
    def update_seller_metrics(self) -> None:
        """Update seller's cached metrics in database."""
        self.seller.total_orders = self.metrics['completed_orders']
        self.seller.total_sales_volume = self.metrics['total_sales_volume']
        self.seller.average_delivery_days = self.metrics['average_delivery_days']
        self.seller.average_rating = self.metrics['average_rating']
        self.seller.return_rate = self.metrics['return_rate']
        self.seller.last_evaluated_at = timezone.now()
        self.seller.save(update_fields=[
            'total_orders', 'total_sales_volume', 'average_delivery_days',
            'average_rating', 'return_rate', 'last_evaluated_at'
        ])
    
    def get_metrics(self) -> Dict:
        """Return collected metrics."""
        return self.metrics.copy()
    
    def get_score_breakdown(self) -> Dict:
        """Return score breakdown for transparency."""
        return self.score_breakdown.copy()
    
    @classmethod
    def evaluate_seller(cls, seller) -> Decimal:
        """
        Convenience method to calculate and update seller performance.
        
        Args:
            seller: Seller model instance
        
        Returns:
            Decimal: Calculated performance score
        """
        service = cls(seller)
        score = service.calculate_performance_score()
        
        # Update metrics
        service.update_seller_metrics()
        
        # Update score
        seller.performance_score = score
        seller.save(update_fields=['performance_score'])
        
        return score

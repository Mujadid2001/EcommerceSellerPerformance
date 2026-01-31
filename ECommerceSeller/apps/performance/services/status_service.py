"""
Status Assignment Service

Automatically assigns seller status based on performance score.
"""
from decimal import Decimal
from django.utils import timezone
from typing import Optional


class StatusAssignmentService:
    """
    Service for automatically assigning seller status based on performance.
    
    Status Classification:
    - Active: Score >= 70
    - Under Review: Score 40-70
    - Suspended: Score < 40
    """
    
    # Status thresholds
    ACTIVE_THRESHOLD = Decimal('70.00')
    UNDER_REVIEW_THRESHOLD = Decimal('40.00')
    
    def __init__(self, seller):
        """
        Initialize service with a seller instance.
        
        Args:
            seller: Seller model instance
        """
        self.seller = seller
        self.previous_status = seller.status
    
    def assign_status(self) -> str:
        """
        Assign status to seller based on current performance score.
        
        Returns:
            str: New status value
        """
        from apps.performance.models import Seller
        
        score = self.seller.performance_score
        new_status = self._determine_status(score)
        
        # Update status if changed
        if new_status != self.seller.status:
            self.seller.status = new_status
            self.seller.status_updated_at = timezone.now()
            self.seller.save(update_fields=['status', 'status_updated_at'])
        
        return new_status
    
    def _determine_status(self, score: Decimal) -> str:
        """
        Determine appropriate status based on score.
        
        Args:
            score: Performance score (0-100)
        
        Returns:
            str: Status choice value
        """
        from apps.performance.models import Seller
        
        if score >= self.ACTIVE_THRESHOLD:
            return Seller.Status.ACTIVE
        elif score >= self.UNDER_REVIEW_THRESHOLD:
            return Seller.Status.UNDER_REVIEW
        else:
            return Seller.Status.SUSPENDED
    
    def status_changed(self) -> bool:
        """Check if status was changed."""
        return self.previous_status != self.seller.status
    
    def get_status_change_info(self) -> Optional[dict]:
        """
        Get information about status change.
        
        Returns:
            dict or None: Status change information if status changed
        """
        if not self.status_changed():
            return None
        
        return {
            'previous_status': self.previous_status,
            'new_status': self.seller.status,
            'changed_at': self.seller.status_updated_at,
            'performance_score': self.seller.performance_score,
        }
    
    @classmethod
    def evaluate_and_assign(cls, seller) -> tuple:
        """
        Convenience method to evaluate performance and assign status.
        
        Args:
            seller: Seller model instance
        
        Returns:
            tuple: (new_status, status_changed)
        """
        from apps.performance.services import PerformanceCalculationService
        
        # Calculate performance score
        PerformanceCalculationService.evaluate_seller(seller)
        
        # Assign status
        service = cls(seller)
        new_status = service.assign_status()
        status_changed = service.status_changed()
        
        return new_status, status_changed
    
    @classmethod
    def bulk_evaluate_sellers(cls, queryset=None) -> dict:
        """
        Evaluate and assign status for multiple sellers.
        
        Args:
            queryset: Optional queryset of sellers. If None, evaluates all sellers.
        
        Returns:
            dict: Summary of evaluations
        """
        from apps.performance.models import Seller
        from apps.performance.services import PerformanceCalculationService
        
        if queryset is None:
            queryset = Seller.objects.all()
        
        summary = {
            'total_evaluated': 0,
            'status_changes': 0,
            'status_distribution': {
                'active': 0,
                'under_review': 0,
                'suspended': 0,
            },
            'errors': []
        }
        
        for seller in queryset:
            try:
                # Evaluate performance
                PerformanceCalculationService.evaluate_seller(seller)
                
                # Assign status
                service = cls(seller)
                service.assign_status()
                
                summary['total_evaluated'] += 1
                
                if service.status_changed():
                    summary['status_changes'] += 1
                
                # Update distribution
                if seller.status == Seller.Status.ACTIVE:
                    summary['status_distribution']['active'] += 1
                elif seller.status == Seller.Status.UNDER_REVIEW:
                    summary['status_distribution']['under_review'] += 1
                elif seller.status == Seller.Status.SUSPENDED:
                    summary['status_distribution']['suspended'] += 1
                    
            except Exception as e:
                summary['errors'].append({
                    'seller_id': seller.id,
                    'error': str(e)
                })
        
        return summary

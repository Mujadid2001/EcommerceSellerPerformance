"""
Signals for automatic performance updates

Automatically triggers performance recalculation when relevant data changes.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from apps.performance.models import Order, CustomerFeedback
from apps.performance.services import StatusAssignmentService


@receiver(post_save, sender=Order)
def order_saved_handler(sender, instance, created, **kwargs):
    """
    Trigger performance recalculation when order is created or updated.
    
    Recalculates when:
    - Order status changes to delivered
    - Order is marked as returned
    """
    # Only recalculate for meaningful status changes
    if instance.status == Order.Status.DELIVERED or instance.is_returned:
        # Use transaction.on_commit to ensure order is saved before recalculation
        transaction.on_commit(
            lambda: _recalculate_seller_performance(instance.seller)
        )


@receiver(post_delete, sender=Order)
def order_deleted_handler(sender, instance, **kwargs):
    """
    Trigger performance recalculation when order is deleted.
    """
    # Use transaction.on_commit to ensure deletion is committed
    transaction.on_commit(
        lambda: _recalculate_seller_performance(instance.seller)
    )


@receiver(post_save, sender=CustomerFeedback)
def feedback_saved_handler(sender, instance, created, **kwargs):
    """
    Trigger performance recalculation when feedback is created or updated.
    """
    transaction.on_commit(
        lambda: _recalculate_seller_performance(instance.seller)
    )


@receiver(post_delete, sender=CustomerFeedback)
def feedback_deleted_handler(sender, instance, **kwargs):
    """
    Trigger performance recalculation when feedback is deleted.
    """
    transaction.on_commit(
        lambda: _recalculate_seller_performance(instance.seller)
    )


def _recalculate_seller_performance(seller):
    """
    Helper function to recalculate seller performance and assign status.
    
    Args:
        seller: Seller instance
    """
    try:
        # Refresh seller from database to avoid stale data
        seller.refresh_from_db()
        
        # Evaluate and assign status
        StatusAssignmentService.evaluate_and_assign(seller)
    except Exception as e:
        # Log error but don't raise to avoid breaking the transaction
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error recalculating performance for seller {seller.id}: {str(e)}")

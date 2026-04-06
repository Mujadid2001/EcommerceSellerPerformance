"""
Signals for automatic performance updates

Automatically triggers performance recalculation when relevant data changes.
Also handles automatic seller profile creation for new users.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.performance.models import Order, CustomerFeedback, Seller
from apps.performance.services import StatusAssignmentService

User = get_user_model()


@receiver(post_save, sender=User)
def create_seller_profile(sender, instance, created, **kwargs):
    """
    Automatically create a Seller profile when a new user with SELLER role registers.
    Only users specifically registering as sellers get seller profiles.
    Uses the business_name from registration if provided.
    """
    if created and not instance.is_superuser and instance.role == 'seller':
        # Generate unique business registration number
        business_reg = f"BRN{instance.id:06d}"
        
        # Get business name from registration or create default
        if hasattr(instance, '_business_name') and instance._business_name:
            business_name = instance._business_name
        else:
            # Fallback: use name or email prefix
            if instance.first_name and instance.last_name:
                business_name = f"{instance.first_name} {instance.last_name}'s Store"
            else:
                business_name = f"{instance.email.split('@')[0]}'s Store"
        
        # Create seller profile
        Seller.objects.create(
            user=instance,
            business_name=business_name,
            business_registration=business_reg,
            description="Welcome to our marketplace! Please update your business description and start adding products.",
            status=Seller.Status.ACTIVE
        )
        
        # Clean up temporary attribute
        if hasattr(instance, '_business_name'):
            delattr(instance, '_business_name')


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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Refresh seller from database to avoid stale data
        seller.refresh_from_db()
        
        # Evaluate and assign status
        StatusAssignmentService.evaluate_and_assign(seller)
        
    except Exception as e:
        # Log error but don't raise to avoid breaking the transaction
        logger.exception(f"Error recalculating performance for seller {seller.id}: {str(e)}")

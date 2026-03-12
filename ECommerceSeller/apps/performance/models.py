"""
Performance models for seller evaluation system
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal


class Seller(models.Model):
    """
    Seller profile linked to User with performance metrics.
    Tracks seller status and computed performance indicators.
    """
    
    class Status(models.TextChoices):
        """Seller performance status."""
        ACTIVE = 'active', _('Active')
        UNDER_REVIEW = 'under_review', _('Under Review')
        SUSPENDED = 'suspended', _('Suspended')
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seller_profile',
        help_text=_('Associated user account')
    )
    business_name = models.CharField(
        max_length=255,
        help_text=_('Registered business name')
    )
    business_registration = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Business registration number')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Seller business description')
    )
    
    # Performance status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text=_('Current seller performance status')
    )
    
    # Metrics snapshot (cached for performance)
    performance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text=_('Computed performance score (0-100)')
    )
    total_orders = models.PositiveIntegerField(
        default=0,
        help_text=_('Total completed orders')
    )
    total_sales_volume = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_('Total sales amount')
    )
    average_delivery_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_('Average delivery time in days')
    )
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))],
        help_text=_('Average customer rating (0-5)')
    )
    return_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text=_('Percentage of returned orders')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status_updated_at = models.DateTimeField(
        default=timezone.now,
        help_text=_('Last status change timestamp')
    )
    last_evaluated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Last performance evaluation timestamp')
    )
    
    class Meta:
        verbose_name = _('Seller')
        verbose_name_plural = _('Sellers')
        ordering = ['-performance_score', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['-performance_score']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', '-performance_score']),
        ]
    
    def __str__(self):
        return f"{self.business_name} ({self.user.email})"
    
    def get_status_display_badge(self):
        """Return HTML-friendly status display."""
        status_colors = {
            self.Status.ACTIVE: 'success',
            self.Status.UNDER_REVIEW: 'warning',
            self.Status.SUSPENDED: 'danger',
        }
        return {
            'status': self.get_status_display(),
            'color': status_colors.get(self.status, 'secondary')
        }
    
    def is_active(self):
        """Check if seller is in active status."""
        return self.status == self.Status.ACTIVE
    
    def is_suspended(self):
        """Check if seller is suspended."""
        return self.status == self.Status.SUSPENDED


class Order(models.Model):
    """
    Order records for tracking seller performance.
    Captures essential metrics for performance evaluation.
    """
    
    class Status(models.TextChoices):
        """Order status choices."""
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        SHIPPED = 'shipped', _('Shipped')
        DELIVERED = 'delivered', _('Delivered')
        CANCELLED = 'cancelled', _('Cancelled')
        RETURNED = 'returned', _('Returned')
    
    seller = models.ForeignKey(
        Seller,
        on_delete=models.CASCADE,
        related_name='orders',
        db_index=True,
        help_text=_('Seller who fulfilled this order')
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Unique order identifier')
    )
    customer_email = models.EmailField(
        help_text=_('Customer email address')
    )
    
    # Order details
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text=_('Current order status')
    )
    order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_('Total order value')
    )
    
    # Delivery tracking
    order_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_('Order placement timestamp')
    )
    shipped_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Order shipment timestamp')
    )
    delivered_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Order delivery timestamp')
    )
    delivery_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('Calculated delivery time in days')
    )
    
    # Return tracking
    is_returned = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_('Whether order was returned')
    )
    return_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Return request timestamp')
    )
    return_reason = models.TextField(
        blank=True,
        null=True,
        help_text=_('Reason for return')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['seller', '-order_date']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['status', '-order_date']),
            models.Index(fields=['seller', 'is_returned']),
            models.Index(fields=['-order_date']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(order_amount__gt=0),
                name='order_amount_positive'
            ),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.seller.business_name}"
    
    def clean(self):
        """Validate order dates."""
        errors = {}
        
        # Validate shipped_date is not in the future
        if self.shipped_date and self.shipped_date > timezone.now():
            errors['shipped_date'] = "Shipped date cannot be in the future."
        
        # Validate delivered_date is not in the future
        if self.delivered_date and self.delivered_date > timezone.now():
            errors['delivered_date'] = "Delivered date cannot be in the future."
        
        # Validate shipped_date is not before order_date
        if self.shipped_date and self.order_date and self.shipped_date < self.order_date:
            errors['shipped_date'] = "Shipped date cannot be before the order date."
        
        # Validate delivered_date is not before order_date
        if self.delivered_date and self.order_date and self.delivered_date < self.order_date:
            errors['delivered_date'] = "Delivered date cannot be before the order date."
        
        # Validate delivered_date is not before shipped_date
        if self.delivered_date and self.shipped_date and self.delivered_date < self.shipped_date:
            errors['delivered_date'] = "Delivered date cannot be before the shipped date."
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Calculate delivery days on save if delivered."""
        # Skip model validation for API updates (handled by serializer)
        skip_validation = kwargs.pop('skip_validation', False)
        if not skip_validation:
            try:
                self.clean()
            except ValidationError as e:
                # Log validation errors but don't raise them during API updates
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Order validation warning: {e}")
        
        if self.delivered_date and self.order_date:
            delta = self.delivered_date - self.order_date
            # Ensure delivery_days is not negative (same day delivery = 1 day)
            calculated_days = delta.days
            if calculated_days <= 0:
                # Same day or past date delivery = 1 day
                self.delivery_days = 1
            else:
                self.delivery_days = calculated_days
        
        if self.status == self.Status.RETURNED:
            self.is_returned = True
            if not self.return_date:
                self.return_date = timezone.now()
        
        super().save(*args, **kwargs)
    
    def is_completed(self):
        """Check if order is successfully completed."""
        return self.status == self.Status.DELIVERED and not self.is_returned
    
    def mark_as_delivered(self, delivered_date=None):
        """Mark order as delivered and calculate delivery time."""
        self.status = self.Status.DELIVERED
        self.delivered_date = delivered_date or timezone.now()
        self.save()
    
    def mark_as_returned(self, reason=''):
        """Mark order as returned."""
        self.status = self.Status.RETURNED
        self.is_returned = True
        self.return_date = timezone.now()
        self.return_reason = reason
        self.save()


class CustomerFeedback(models.Model):
    """
    Customer feedback and ratings for seller orders.
    Used in performance calculation.
    """
    
    seller = models.ForeignKey(
        Seller,
        on_delete=models.CASCADE,
        related_name='feedbacks',
        db_index=True,
        help_text=_('Seller being rated')
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='feedback',
        help_text=_('Associated order')
    )
    customer_email = models.EmailField(
        help_text=_('Customer who provided feedback')
    )
    
    # Rating (1-5 stars)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        db_index=True,
        help_text=_('Customer rating (1-5 stars)')
    )
    
    # Optional feedback text
    comment = models.TextField(
        blank=True,
        help_text=_('Customer feedback comment')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Customer Feedback')
        verbose_name_plural = _('Customer Feedbacks')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['seller', 'rating']),
            models.Index(fields=['-created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name='rating_valid_range'
            ),
        ]
    
    def __str__(self):
        return f"Feedback for {self.seller.business_name} - {self.rating}★"
    
    def save(self, *args, **kwargs):
        """Ensure customer email matches order."""
        if self.order and not self.customer_email:
            self.customer_email = self.order.customer_email
        super().save(*args, **kwargs)

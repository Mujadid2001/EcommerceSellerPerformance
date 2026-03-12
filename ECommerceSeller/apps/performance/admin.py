"""
Django Admin configuration for Performance app
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from apps.performance.models import Seller, Order, CustomerFeedback
from apps.performance.services import PerformanceCalculationService, StatusAssignmentService


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    """Admin interface for Seller model with performance dashboard."""
    
    list_display = [
        'business_name',
        'user_email',
        'status_badge',
        'performance_score_display',
        'total_orders_display',
        'sales_volume_display',
        'average_rating_display',
        'return_rate_display',
        'last_evaluated',
        'actions_column'
    ]
    
    list_filter = [
        'status',
        'created_at',
        'status_updated_at',
    ]
    
    search_fields = [
        'business_name',
        'business_registration',
        'user__email',
        'user__first_name',
        'user__last_name',
    ]
    
    readonly_fields = [
        'performance_score',
        'total_orders',
        'total_sales_volume',
        'average_delivery_days',
        'average_rating',
        'return_rate',
        'created_at',
        'updated_at',
        'status_updated_at',
        'last_evaluated_at',
        'detailed_metrics_display',
        'score_breakdown_display',
    ]
    
    fieldsets = (
        (_('Business Information'), {
            'fields': ('user', 'business_name', 'business_registration', 'description')
        }),
        (_('Performance Status'), {
            'fields': ('status', 'status_updated_at', 'performance_score')
        }),
        (_('Performance Metrics'), {
            'fields': (
                'total_orders',
                'total_sales_volume',
                'average_delivery_days',
                'average_rating',
                'return_rate',
            )
        }),
        (_('Detailed Analysis'), {
            'fields': ('detailed_metrics_display', 'score_breakdown_display'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'last_evaluated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['recalculate_performance', 'activate_sellers', 'suspend_sellers']
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    # Custom display methods
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = _('User Email')
    user_email.admin_order_field = 'user__email'
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'active': '#28a745',
            'under_review': '#ffc107',
            'suspended': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'status'
    
    def performance_score_display(self, obj):
        """Display performance score with color coding."""
        score = obj.performance_score
        if score >= Decimal('70.00'):
            color = '#28a745'
        elif score >= Decimal('40.00'):
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 14px;">{}</span>',
            color,
            f"{score:.2f}"
        )
    performance_score_display.short_description = _('Score')
    performance_score_display.admin_order_field = 'performance_score'
    
    def total_orders_display(self, obj):
        """Display total orders."""
        return f"{obj.total_orders:,}"
    total_orders_display.short_description = _('Orders')
    total_orders_display.admin_order_field = 'total_orders'
    
    def sales_volume_display(self, obj):
        """Display sales volume formatted."""
        return f"${obj.total_sales_volume:,.2f}"
    sales_volume_display.short_description = _('Sales')
    sales_volume_display.admin_order_field = 'total_sales_volume'
    
    def average_rating_display(self, obj):
        """Display average rating with stars."""
        rating = obj.average_rating
        if rating > 0:
            stars = '★' * int(rating) + '☆' * (5 - int(rating))
            return format_html(
                '<span title="{:.2f}">{}</span>',
                rating,
                stars
            )
        return '-'
    average_rating_display.short_description = _('Rating')
    average_rating_display.admin_order_field = 'average_rating'
    
    def return_rate_display(self, obj):
        """Display return rate with color coding."""
        rate = obj.return_rate
        if rate <= Decimal('5.00'):
            color = '#28a745'
        elif rate <= Decimal('10.00'):
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {};">{:.2f}%</span>',
            color,
            rate
        )
    return_rate_display.short_description = _('Returns')
    return_rate_display.admin_order_field = 'return_rate'
    
    def last_evaluated(self, obj):
        """Display last evaluation time."""
        if obj.last_evaluated_at:
            return timezone.localtime(obj.last_evaluated_at).strftime('%Y-%m-%d %H:%M')
        return _('Never')
    last_evaluated.short_description = _('Last Evaluated')
    last_evaluated.admin_order_field = 'last_evaluated_at'
    
    def actions_column(self, obj):
        """Display action buttons."""
        return format_html(
            '<a class="button" href="#" onclick="location.href=\'{}?ids={}\'; return false;">Recalculate</a>',
            reverse('admin:performance_seller_changelist'),
            obj.id
        )
    actions_column.short_description = _('Actions')
    
    def detailed_metrics_display(self, obj):
        """Display detailed metrics in admin detail view."""
        service = PerformanceCalculationService(obj)
        service._gather_metrics()
        metrics = service.get_metrics()
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f8f9fa;"><th style="padding: 8px; text-align: left;">Metric</th><th style="padding: 8px; text-align: right;">Value</th></tr>'
        
        metrics_display = [
            ('Total Orders', f"{metrics['total_orders']:,}"),
            ('Completed Orders', f"{metrics['completed_orders']:,}"),
            ('Returned Orders', f"{metrics['returned_orders']:,}"),
            ('Sales Volume', f"${metrics['total_sales_volume']:,.2f}"),
            ('Avg Delivery Days', f"{metrics['average_delivery_days']:.2f}"),
            ('Return Rate', f"{metrics['return_rate']:.2f}%"),
            ('Average Rating', f"{metrics['average_rating']:.2f} / 5.00"),
            ('Feedback Count', f"{metrics['feedback_count']:,}"),
        ]
        
        for label, value in metrics_display:
            html += f'<tr><td style="padding: 8px; border-top: 1px solid #dee2e6;">{label}</td>'
            html += f'<td style="padding: 8px; text-align: right; border-top: 1px solid #dee2e6;"><strong>{value}</strong></td></tr>'
        
        html += '</table>'
        return format_html(html)
    detailed_metrics_display.short_description = _('Detailed Metrics')
    
    def score_breakdown_display(self, obj):
        """Display score breakdown in admin detail view."""
        service = PerformanceCalculationService(obj)
        service.calculate_performance_score()
        breakdown = service.get_score_breakdown()
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f8f9fa;"><th style="padding: 8px; text-align: left;">Component</th>'
        html += '<th style="padding: 8px; text-align: right;">Score</th>'
        html += '<th style="padding: 8px; text-align: right;">Weight</th>'
        html += '<th style="padding: 8px; text-align: right;">Weighted</th></tr>'
        
        components = [
            ('Sales Volume', breakdown['sales_score'], breakdown['weights']['sales']),
            ('Delivery Speed', breakdown['delivery_score'], breakdown['weights']['delivery']),
            ('Customer Rating', breakdown['rating_score'], breakdown['weights']['rating']),
            ('Returns (Penalty)', breakdown['returns_penalty'], breakdown['weights']['returns']),
        ]
        
        for label, score, weight in components:
            weighted = (score * weight / Decimal('100.00'))
            html += f'<tr><td style="padding: 8px; border-top: 1px solid #dee2e6;">{label}</td>'
            html += f'<td style="padding: 8px; text-align: right; border-top: 1px solid #dee2e6;">{score:.2f}</td>'
            html += f'<td style="padding: 8px; text-align: right; border-top: 1px solid #dee2e6;">{weight}%</td>'
            html += f'<td style="padding: 8px; text-align: right; border-top: 1px solid #dee2e6;"><strong>{weighted:.2f}</strong></td></tr>'
        
        html += '<tr style="background-color: #e9ecef; font-weight: bold;">'
        html += '<td style="padding: 8px; border-top: 2px solid #495057;">Total Score</td>'
        html += '<td style="padding: 8px; border-top: 2px solid #495057;"></td>'
        html += '<td style="padding: 8px; border-top: 2px solid #495057;"></td>'
        html += f'<td style="padding: 8px; text-align: right; border-top: 2px solid #495057;">{breakdown["total_score"]:.2f}</td></tr>'
        html += '</table>'
        
        return format_html(html)
    score_breakdown_display.short_description = _('Score Breakdown')
    
    # Admin actions
    
    @admin.action(description=_('Recalculate performance for selected sellers'))
    def recalculate_performance(self, request, queryset):
        """Recalculate performance for selected sellers."""
        count = 0
        for seller in queryset:
            StatusAssignmentService.evaluate_and_assign(seller)
            count += 1
        
        self.message_user(request, _(f'Successfully recalculated performance for {count} seller(s).'))
    
    @admin.action(description=_('Set selected sellers to Active'))
    def activate_sellers(self, request, queryset):
        """Activate selected sellers."""
        count = queryset.update(
            status=Seller.Status.ACTIVE,
            status_updated_at=timezone.now()
        )
        self.message_user(request, _(f'Successfully activated {count} seller(s).'))
    
    @admin.action(description=_('Suspend selected sellers'))
    def suspend_sellers(self, request, queryset):
        """Suspend selected sellers."""
        count = queryset.update(
            status=Seller.Status.SUSPENDED,
            status_updated_at=timezone.now()
        )
        self.message_user(request, _(f'Successfully suspended {count} seller(s).'))


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model."""
    
    list_display = [
        'order_number',
        'seller_name',
        'customer_email',
        'status_badge',
        'order_amount_display',
        'order_date_display',
        'delivery_days_display',
        'is_returned',
    ]
    
    list_filter = [
        'status',
        'is_returned',
        'order_date',
        'seller',
    ]
    
    search_fields = [
        'order_number',
        'customer_email',
        'seller__business_name',
        'seller__user__email',
    ]
    
    readonly_fields = [
        'order_number',
        'delivery_days',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        (_('Order Information'), {
            'fields': ('order_number', 'seller', 'customer_email', 'status', 'order_amount')
        }),
        (_('Delivery Tracking'), {
            'fields': ('order_date', 'shipped_date', 'delivered_date', 'delivery_days')
        }),
        (_('Return Information'), {
            'fields': ('is_returned', 'return_date', 'return_reason')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'order_date'
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        qs = super().get_queryset(request)
        return qs.select_related('seller', 'seller__user')
    
    def seller_name(self, obj):
        """Display seller business name."""
        return obj.seller.business_name
    seller_name.short_description = _('Seller')
    seller_name.admin_order_field = 'seller__business_name'
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'pending': '#6c757d',
            'processing': '#17a2b8',
            'shipped': '#007bff',
            'delivered': '#28a745',
            'cancelled': '#6c757d',
            'returned': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'status'
    
    def order_amount_display(self, obj):
        """Display order amount formatted."""
        return f"${obj.order_amount:,.2f}"
    order_amount_display.short_description = _('Amount')
    order_amount_display.admin_order_field = 'order_amount'
    
    def order_date_display(self, obj):
        """Display order date formatted."""
        return timezone.localtime(obj.order_date).strftime('%Y-%m-%d')
    order_date_display.short_description = _('Order Date')
    order_date_display.admin_order_field = 'order_date'
    
    def delivery_days_display(self, obj):
        """Display delivery days with color coding."""
        if obj.delivery_days is None:
            return '-'
        
        days = obj.delivery_days
        if days <= 2:
            color = '#28a745'
        elif days <= 5:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} days</span>',
            color,
            days
        )
    delivery_days_display.short_description = _('Delivery Time')
    delivery_days_display.admin_order_field = 'delivery_days'


@admin.register(CustomerFeedback)
class CustomerFeedbackAdmin(admin.ModelAdmin):
    """Admin interface for CustomerFeedback model."""
    
    list_display = [
        'order_number',
        'seller_name',
        'customer_email',
        'rating_stars',
        'created_at_display',
    ]
    
    list_filter = [
        'rating',
        'created_at',
        'seller',
    ]
    
    search_fields = [
        'customer_email',
        'seller__business_name',
        'order__order_number',
        'comment',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        (_('Feedback Information'), {
            'fields': ('seller', 'order', 'customer_email', 'rating', 'comment')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        qs = super().get_queryset(request)
        return qs.select_related('seller', 'order', 'seller__user')
    
    def order_number(self, obj):
        """Display order number."""
        return obj.order.order_number
    order_number.short_description = _('Order')
    order_number.admin_order_field = 'order__order_number'
    
    def seller_name(self, obj):
        """Display seller business name."""
        return obj.seller.business_name
    seller_name.short_description = _('Seller')
    seller_name.admin_order_field = 'seller__business_name'
    
    def rating_stars(self, obj):
        """Display rating as stars."""
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        color = '#ffc107' if obj.rating >= 3 else '#dc3545'
        return format_html(
            '<span style="color: {}; font-size: 16px;">{}</span>',
            color,
            stars
        )
    rating_stars.short_description = _('Rating')
    rating_stars.admin_order_field = 'rating'
    
    def created_at_display(self, obj):
        """Display creation date formatted."""
        return timezone.localtime(obj.created_at).strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = _('Created')
    created_at_display.admin_order_field = 'created_at'

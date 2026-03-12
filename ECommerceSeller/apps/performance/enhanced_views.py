"""
Enhanced Dashboard Views with AI Integration.
Implements FR-06: View Personal Dashboard and FR-07: Access Personal Performance Reports.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import timedelta
import json

from .models import Seller, Order, CustomerFeedback
from apps.ai_insights.models import PerformanceInsight, PredictiveAlert, RankingChange
from apps.ai_insights.services.ai_service import AIInsightService
from apps.performance.services.import_export.export_service import ExportService
from apps.authentication.middleware import user_required, role_required


@login_required
@user_required
def enhanced_seller_dashboard(request):
    """
    Enhanced seller dashboard with AI insights and comprehensive metrics.
    Implements FR-06: View Personal Dashboard with AI features.
    """
    # Check if user has seller profile
    if not hasattr(request.user, 'seller_profile'):
        return render(request, 'performance/no_profile.html')
    
    seller = request.user.seller_profile
    
    # Get time period from query params (default: last 30 days)
    period_days = int(request.GET.get('period', 30))
    start_date = timezone.now() - timedelta(days=period_days)
    
    # Performance metrics
    orders_queryset = Order.objects.filter(seller=seller, order_date__gte=start_date)
    
    metrics = {
        'total_orders': orders_queryset.count(),
        'completed_orders': orders_queryset.filter(status=Order.Status.DELIVERED).count(),
        'pending_orders': orders_queryset.filter(
            status__in=[Order.Status.PENDING, Order.Status.PROCESSING, Order.Status.SHIPPED]
        ).count(),
        'returned_orders': orders_queryset.filter(is_returned=True).count(),
        'total_revenue': orders_queryset.aggregate(Sum('order_amount'))['order_amount__sum'] or 0,
        'avg_order_value': orders_queryset.aggregate(Avg('order_amount'))['order_amount__avg'] or 0,
    }
    
    # Calculate rates
    if metrics['total_orders'] > 0:
        metrics['completion_rate'] = (metrics['completed_orders'] / metrics['total_orders']) * 100
        metrics['return_rate'] = (metrics['returned_orders'] / metrics['total_orders']) * 100
    else:
        metrics['completion_rate'] = 0
        metrics['return_rate'] = 0
    
    # Recent feedback
    feedback = CustomerFeedback.objects.filter(
        order__seller=seller,
        created_at__gte=start_date
    ).order_by('-created_at')[:5]
    
    avg_rating = CustomerFeedback.objects.filter(
        order__seller=seller,
        created_at__gte=start_date
    ).aggregate(Avg('rating'))['rating__avg'] or 0
    
    # AI Insights
    ai_insights = PerformanceInsight.objects.filter(
        seller=seller,
        status=PerformanceInsight.Status.ACTIVE
    ).order_by('-created_at')[:5]
    
    # Predictive Alerts
    active_alerts = PredictiveAlert.objects.filter(
        seller=seller,
        is_active=True
    ).order_by('-created_at')[:3]
    
    # Performance trends (for charts)
    trends_data = _get_performance_trends(seller, period_days)
    
    # Ranking information
    current_ranking = _get_seller_ranking(seller)
    recent_ranking_changes = RankingChange.objects.filter(
        seller=seller
    ).order_by('-change_date')[:5]
    
    context = {
        'seller': seller,
        'metrics': metrics,
        'avg_rating': round(avg_rating, 2),
        'recent_feedback': feedback,
        'ai_insights': ai_insights,
        'active_alerts': active_alerts,
        'trends_data': json.dumps(trends_data),
        'current_ranking': current_ranking,
        'recent_ranking_changes': recent_ranking_changes,
        'period_days': period_days,
        'available_periods': [7, 30, 90, 365],
    }
    
    return render(request, 'performance/enhanced_dashboard.html', context)


@login_required
def seller_performance_report(request):
    """
    Generate and display comprehensive performance report for seller.
    Implements FR-07: Access Personal Performance Reports.
    """
    if not hasattr(request.user, 'seller_profile'):
        messages.error(request, 'No seller profile found.')
        return redirect('performance:marketplace')
    
    seller = request.user.seller_profile
    
    # Time period selection
    period_days = int(request.GET.get('period', 90))
    start_date = timezone.now() - timedelta(days=period_days)
    
    # Comprehensive metrics
    orders = Order.objects.filter(seller=seller, order_date__gte=start_date)
    all_orders = Order.objects.filter(seller=seller)
    
    report_data = {
        'period_summary': {
            'total_orders': orders.count(),
            'total_revenue': orders.aggregate(Sum('order_amount'))['order_amount__sum'] or 0,
            'avg_order_value': orders.aggregate(Avg('order_amount'))['order_amount__avg'] or 0,
            'completion_rate': 0,
            'return_rate': 0,
            'avg_delivery_days': 0,
        },
        'historical_comparison': {
            'total_orders_all_time': all_orders.count(),
            'total_revenue_all_time': all_orders.aggregate(Sum('order_amount'))['order_amount__sum'] or 0,
            'performance_score': float(seller.performance_score),
            'status': seller.get_status_display(),
        }
    }
    
    # Calculate rates
    if orders.count() > 0:
        completed = orders.filter(status=Order.Status.DELIVERED).count()
        returned = orders.filter(is_returned=True).count()
        
        report_data['period_summary']['completion_rate'] = (completed / orders.count()) * 100
        report_data['period_summary']['return_rate'] = (returned / orders.count()) * 100
        
        # Average delivery days for completed orders
        avg_delivery = orders.filter(
            status=Order.Status.DELIVERED,
            delivery_days__isnull=False
        ).aggregate(Avg('delivery_days'))['delivery_days__avg'] or 0
        
        report_data['period_summary']['avg_delivery_days'] = avg_delivery
    
    # Customer feedback analysis
    feedback = CustomerFeedback.objects.filter(
        order__seller=seller,
        created_at__gte=start_date
    )
    
    feedback_analysis = {
        'total_feedback': feedback.count(),
        'avg_rating': feedback.aggregate(Avg('rating'))['rating__avg'] or 0,
        'rating_distribution': {}
    }
    
    # Rating distribution
    for rating in range(1, 6):
        count = feedback.filter(rating=rating).count()
        feedback_analysis['rating_distribution'][rating] = count
    
    # AI Analysis (if available)
    ai_service = AIInsightService()
    ai_analysis = ai_service.analyze_seller_performance(seller)
    
    context = {
        'seller': seller,
        'report_data': report_data,
        'feedback_analysis': feedback_analysis,
        'ai_analysis': ai_analysis,
        'period_days': period_days,
        'start_date': start_date,
        'available_periods': [30, 90, 180, 365],
        'recent_orders': orders.order_by('-order_date')[:10],
        'recent_feedback': feedback.order_by('-created_at')[:5]
    }
    
    return render(request, 'performance/seller_report.html', context)


@login_required
def download_seller_report(request):
    """
    Download seller performance report as PDF.
    Implements part of FR-07: Download personal performance reports.
    """
    if not hasattr(request.user, 'seller_profile'):
        messages.error(request, 'No seller profile found.')
        return redirect('performance:marketplace')
    
    seller = request.user.seller_profile
    export_format = request.GET.get('format', 'pdf')
    
    try:
        export_service = ExportService()
        
        if export_format == 'pdf':
            pdf_buffer = export_service.generate_seller_report_pdf(seller, request.user)
            
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            filename = f"performance_report_{seller.business_name}_{timezone.now().strftime('%Y%m%d')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
        
        else:
            messages.error(request, 'Unsupported export format.')
            return redirect('performance:seller_report')
    
    except Exception as e:
        messages.error(request, f'Failed to generate report: {str(e)}')
        return redirect('performance:seller_report')


@login_required
def ai_insights_view(request):
    """
    Display AI insights and recommendations for seller.
    """
    if not hasattr(request.user, 'seller_profile'):
        messages.error(request, 'No seller profile found.')
        return redirect('performance:marketplace')
    
    seller = request.user.seller_profile
    
    # Get insights by type
    insights_by_type = {}
    for insight_type, display_name in PerformanceInsight.InsightType.choices:
        insights = PerformanceInsight.objects.filter(
            seller=seller,
            insight_type=insight_type,
            status=PerformanceInsight.Status.ACTIVE
        ).order_by('-created_at')
        
        if insights:
            insights_by_type[display_name] = insights
    
    # Get active alerts
    alerts = PredictiveAlert.objects.filter(
        seller=seller,
        is_active=True
    ).order_by('-created_at')
    
    # Trigger new AI analysis if requested
    if request.GET.get('refresh') == 'true':
        try:
            ai_service = AIInsightService()
            ai_service.analyze_seller_performance(seller)
            messages.success(request, 'AI analysis updated successfully.')
        except Exception as e:
            messages.error(request, f'Failed to update AI analysis: {str(e)}')
        
        return redirect('performance:ai_insights')
    
    context = {
        'seller': seller,
        'insights_by_type': insights_by_type,
        'alerts': alerts,
        'total_insights': sum(len(insights) for insights in insights_by_type.values()),
        'total_alerts': alerts.count()
    }
    
    return render(request, 'performance/ai_insights.html', context)


@login_required
def acknowledge_insight(request, insight_id):
    """Acknowledge an AI insight."""
    try:
        insight = get_object_or_404(
            PerformanceInsight,
            id=insight_id,
            seller=request.user.seller_profile
        )
        
        insight.acknowledge(request.user)
        messages.success(request, 'Insight acknowledged successfully.')
    
    except Exception as e:
        messages.error(request, f'Failed to acknowledge insight: {str(e)}')
    
    return redirect('performance:ai_insights')


@login_required
def acknowledge_alert(request, alert_id):
    """Acknowledge a predictive alert."""
    try:
        alert = get_object_or_404(
            PredictiveAlert,
            id=alert_id,
            seller=request.user.seller_profile
        )
        
        alert.acknowledge(request.user)
        messages.success(request, 'Alert acknowledged successfully.')
    
    except Exception as e:
        messages.error(request, f'Failed to acknowledge alert: {str(e)}')
    
    return redirect('performance:ai_insights')


def _get_performance_trends(seller, period_days):
    """Get performance trends data for charts."""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=period_days)
    
    # Group data by days/weeks based on period
    if period_days <= 30:
        # Daily data for periods <= 30 days
        interval_days = 1
        date_format = '%Y-%m-%d'
    else:
        # Weekly data for longer periods
        interval_days = 7
        date_format = '%Y-W%W'
    
    trends = {
        'labels': [],
        'orders': [],
        'revenue': [],
        'ratings': []
    }
    
    current_date = start_date
    while current_date <= end_date:
        next_date = current_date + timedelta(days=interval_days)
        
        # Get orders in this interval
        interval_orders = Order.objects.filter(
            seller=seller,
            order_date__gte=current_date,
            order_date__lt=next_date
        )
        
        # Get feedback in this interval
        interval_feedback = CustomerFeedback.objects.filter(
            order__seller=seller,
            created_at__gte=current_date,
            created_at__lt=next_date
        )
        
        trends['labels'].append(current_date.strftime(date_format))
        trends['orders'].append(interval_orders.count())
        trends['revenue'].append(float(interval_orders.aggregate(
            Sum('order_amount'))['order_amount__sum'] or 0))
        trends['ratings'].append(float(interval_feedback.aggregate(
            Avg('rating'))['rating__avg'] or 0))
        
        current_date = next_date
    
    return trends


def _get_seller_ranking(seller):
    """Get current seller ranking among all active sellers."""
    try:
        # Get all active sellers ordered by performance score
        ranked_sellers = Seller.objects.filter(
            status=Seller.Status.ACTIVE
        ).order_by('-performance_score')
        
        # Find current seller's position
        for rank, ranked_seller in enumerate(ranked_sellers, 1):
            if ranked_seller.id == seller.id:
                return {
                    'rank': rank,
                    'total_sellers': ranked_sellers.count(),
                    'percentile': ((ranked_sellers.count() - rank + 1) / ranked_sellers.count()) * 100
                }
        
        return None
    
    except Exception:
        return None
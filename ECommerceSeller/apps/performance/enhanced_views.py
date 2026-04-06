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
from django.conf import settings
from datetime import timedelta
import json
import logging

from .models import Seller, Order, CustomerFeedback
from apps.ai_insights.models import PerformanceInsight, PredictiveAlert, RankingChange
from apps.ai_insights.services.ai_service import AIInsightService
from apps.performance.services.import_export.export_service import ExportService
from apps.authentication.middleware import user_required, role_required

logger = logging.getLogger(__name__)


def calculate_health_score_from_insights(health_insights, default_score=75):
    """Calculate health score from insights queryset (fast, no async)."""
    if not health_insights:
        return default_score
    
    health_insights_list = list(health_insights) if hasattr(health_insights, '__iter__') else []
    total_insights = len(health_insights_list)
    
    if total_insights == 0:
        return default_score
    
    # Weight insights by severity
    critical_count = sum(1 for i in health_insights_list if hasattr(i, 'severity') and i.severity == PerformanceInsight.Severity.CRITICAL)
    high_count = sum(1 for i in health_insights_list if hasattr(i, 'severity') and i.severity == PerformanceInsight.Severity.HIGH)
    
    score = 100
    score -= critical_count * 20
    score -= high_count * 10
    
    return max(0, min(100, score))


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
    
    # Trigger AI insights generation (async if Celery available, else sync)
    try:
        from apps.performance.tasks import generate_ai_insights_for_seller
        # Trigger async AI analysis
        generate_ai_insights_for_seller.delay(seller.id)
    except Exception as e:
        logger.warning(f"Could not trigger async AI insights: {e}. Falling back to sync...")
        try:
            # Use module-level import (already imported at top of file)
            ai_service = AIInsightService()
            # Sync AI analysis
            ai_service.analyze_seller_performance(seller)
        except Exception as ai_error:
            logger.error(f"AI insights generation failed: {ai_error}")
    
    # Get time period from query params (default: last 30 days)
    period_days = int(request.GET.get('period', 30))
    start_date = timezone.now() - timedelta(days=period_days)
    
    # Performance metrics - using service for calculations
    from apps.performance.services.performance_service import PerformanceCalculationService
    
    orders_queryset = Order.objects.filter(seller=seller, order_date__gte=start_date)
    
    metrics = {
        'total_orders': orders_queryset.count(),
        'completed_orders': orders_queryset.filter(status=Order.Status.DELIVERED).count(),
        'pending_orders': orders_queryset.filter(
            status__in=[Order.Status.PENDING, Order.Status.PROCESSING, Order.Status.SHIPPED]
        ).count(),
        'returned_orders': orders_queryset.filter(is_returned=True).count(),
        'total_sales_volume': float(orders_queryset.aggregate(Sum('order_amount'))['order_amount__sum'] or 0),
        'avg_order_value': float(orders_queryset.aggregate(Avg('order_amount'))['order_amount__avg'] or 0),
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
    
    feedback_count = CustomerFeedback.objects.filter(
        order__seller=seller,
        created_at__gte=start_date
    ).count()
    
    # Recent orders with delivery calculation
    recent_orders = orders_queryset.order_by('-order_date')[:10]
    for order in recent_orders:
        if order.delivered_date and order.order_date:
            order.delivery_days = (order.delivered_date - order.order_date).days
        else:
            order.delivery_days = None
    
    # Calculate average delivery days
    avg_delivery_days = 0
    delivered_orders = orders_queryset.filter(status=Order.Status.DELIVERED).exclude(delivered_date__isnull=True)
    if delivered_orders.exists():
        total_days = 0
        count = 0
        for order in delivered_orders:
            if order.delivered_date and order.order_date:
                total_days += (order.delivered_date - order.order_date).days
                count += 1
        avg_delivery_days = total_days / count if count > 0 else 0
    
    metrics['average_rating'] = float(avg_rating)
    metrics['feedback_count'] = feedback_count
    metrics['average_delivery_days'] = float(avg_delivery_days)
    
    # Calculate performance score breakdown using service
    try:
        perf_service = PerformanceCalculationService(seller)
        overall_score = perf_service.calculate_performance_score()
        
        # Read weights from PerformanceConfig database model
        from apps.performance.models import PerformanceConfig
        config = PerformanceConfig.get_config()
        
        breakdown = {
            'sales_score': float(perf_service.score_breakdown.get('sales_score', 0)),
            'delivery_score': float(perf_service.score_breakdown.get('delivery_score', 0)),
            'rating_score': float(perf_service.score_breakdown.get('rating_score', 0)),
            'returns_penalty': float(perf_service.score_breakdown.get('returns_penalty', 0)),
            'total_score': float(overall_score),
            'weights': {
                'sales': config.weight_sales,
                'delivery': config.weight_delivery,
                'rating': config.weight_rating,
                'returns': config.weight_returns,
            },
            'thresholds': {
                'status_active': config.status_threshold_active,
                'status_under_review': config.status_threshold_under_review,
            }
        }
    except Exception as e:
        # Fallback with defaults from settings if config fetch fails
        breakdown = {
            'sales_score': 0,
            'delivery_score': 0,
            'rating_score': 0,
            'returns_penalty': 0,
            'total_score': float(seller.performance_score),
            'weights': {
                'sales': 30,
                'delivery': 25,
                'rating': 35,
                'returns': 10,
            }
        }
    
    # AI Insights - Prominently featured
    ai_insights = PerformanceInsight.objects.filter(
        seller=seller,
        status=PerformanceInsight.Status.ACTIVE
    ).order_by('-created_at')[:5]
    
    # If no insights exist, create a default one to show the feature is active
    if not ai_insights.exists():
        logger.info(f"No insights found for seller {seller.id}, creating default insight...")
        try:
            from decimal import Decimal
            PerformanceInsight.objects.get_or_create(
                seller=seller,
                insight_type=PerformanceInsight.InsightType.HEALTH_CHECK,
                title='Performance Analysis',
                defaults={
                    'severity': PerformanceInsight.Severity.INFO,
                    'description': 'AI is analyzing your performance metrics.',
                    'confidence_score': Decimal('70.00'),
                    'analysis_data': {'status': 'initial_analysis'},
                    'status': PerformanceInsight.Status.ACTIVE,
                    'recommendation': 'Check back shortly for detailed recommendations.'
                }
            )
            # Refresh the queryset
            ai_insights = PerformanceInsight.objects.filter(
                seller=seller,
                status=PerformanceInsight.Status.ACTIVE
            ).order_by('-created_at')[:5]
        except Exception as e:
            logger.error(f"Failed to create default insight: {e}")
    
    # AI Predictions & Recommendations - Optimized for speed (cached results only)
    ai_predictions = PerformanceInsight.objects.filter(
        seller=seller,
        insight_type=PerformanceInsight.InsightType.PREDICTION,
        status=PerformanceInsight.Status.ACTIVE
    ).only('id', 'title', 'description', 'severity', 'confidence_score').order_by('-created_at')[:3]
    
    ai_recommendations = PerformanceInsight.objects.filter(
        seller=seller,
        insight_type=PerformanceInsight.InsightType.RECOMMENDATION,
        status=PerformanceInsight.Status.ACTIVE
    ).only('id', 'title', 'description', 'severity', 'recommendation').order_by('-created_at')[:3]
    
    ai_trends = PerformanceInsight.objects.filter(
        seller=seller,
        insight_type=PerformanceInsight.InsightType.TREND_ANALYSIS,
        status=PerformanceInsight.Status.ACTIVE
    ).only('id', 'title', 'description', 'severity').order_by('-created_at')[:3]
    
    # Predictive Alerts
    active_alerts = PredictiveAlert.objects.filter(
        seller=seller,
        is_active=True
    ).only('id', 'alert_type', 'message', 'severity').order_by('-created_at')[:3]
    
    # Trigger AI generation in background (non-blocking)
    try:
        from apps.performance.tasks import generate_ai_insights_for_seller
        generate_ai_insights_for_seller.delay(seller.id, priority='background')
    except:
        pass  # Fail silently - Celery may not be running
    
    # AI Analysis summary (from cached database records, not synchronous analysis)
    try:
        health_insights = PerformanceInsight.objects.filter(
            seller=seller,
            insight_type=PerformanceInsight.InsightType.PERFORMANCE_ALERT,
            status=PerformanceInsight.Status.ACTIVE
        ).order_by('-created_at')
        
        ai_summary = {
            'health_score': calculate_health_score_from_insights(health_insights),
            'risk_factors': [i.description for i in health_insights[:3]],
            'predictions': {},
            'recommendations': list(ai_recommendations.values_list('recommendation', flat=True)[:5]),
        }
    except Exception as e:
        ai_summary = {'health_score': 0, 'risk_factors': [], 'predictions': {}, 'recommendations': []}
    
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
        'breakdown': breakdown,  # Add score breakdown for template charts
        'recent_feedback': feedback,
        'recent_orders': recent_orders,
        'ai_insights': ai_insights,
        'ai_predictions': ai_predictions,
        'ai_recommendations': ai_recommendations,
        'ai_trends': ai_trends,
        'ai_summary': ai_summary,
        'active_alerts': active_alerts,
        'trends_data': json.dumps(trends_data),
        'current_ranking': current_ranking,
        'recent_ranking_changes': recent_ranking_changes,
        'period_days': period_days,
        'available_periods': [7, 30, 90, 365],
    }
    
    return render(request, 'performance/dashboard.html', context)


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
    
    # Get all active insights
    all_insights = PerformanceInsight.objects.filter(
        seller=seller,
        status=PerformanceInsight.Status.ACTIVE
    ).order_by('-created_at')
    
    # Calculate health score
    health_score = round((seller.performance_score / 100) * 100) if seller.performance_score else 0
    health_summary = f"Your seller performance score is {seller.performance_score:.2f}/100. Keep improving your metrics to maintain excellent status."
    
    context = {
        'seller': seller,
        'insights': all_insights,
        'insights_by_type': insights_by_type,
        'alerts': alerts,
        'health_score': health_score,
        'health_summary': health_summary,
        'total_insights': all_insights.count(),
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


@login_required
@user_required
def performance_predictor(request):
    """
    Interactive Performance Predictor - What-If scenario analysis.
    Allows sellers to adjust metrics and see predicted performance score changes.
    """
    if not hasattr(request.user, 'seller_profile'):
        messages.error(request, 'No seller profile found.')
        return redirect('performance:marketplace')
    
    seller = request.user.seller_profile
    
    # Get current metrics
    current_metrics = {
        'total_sales': float(seller.total_sales_volume),
        'average_rating': float(seller.average_rating),
        'average_delivery_days': float(seller.average_delivery_days),
        'return_rate': float(seller.return_rate),
        'current_score': float(seller.performance_score),
    }
    
    context = {
        'seller': seller,
        'current_metrics': current_metrics,
        'max_sales': max(100000, float(seller.total_sales_volume) * 1.5),
        'max_delivery_days': 30,
        'max_return_rate': 40,
    }
    
    return render(request, 'performance/predictor.html', context)


@login_required
@user_required
def predict_performance_api(request):
    """
    API endpoint for real-time performance prediction.
    Calculates predicted score based on adjusted metrics.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    if not hasattr(request.user, 'seller_profile'):
        return JsonResponse({'error': 'No seller profile found'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        from apps.performance.services.predictor_service import PerformancePredictorService
        
        predictor = PerformancePredictorService()
        
        # Get predicted metrics
        predicted = predictor.calculate_predicted_score(
            total_sales=float(data.get('total_sales', 0)),
            average_rating=float(data.get('average_rating', 0)),
            average_delivery_days=float(data.get('average_delivery_days', 0)),
            return_rate=float(data.get('return_rate', 0))
        )
        
        # Get current seller metrics
        seller = request.user.seller_profile
        current_metrics = {
            'total_sales': float(seller.total_sales_volume),
            'average_rating': float(seller.average_rating),
            'average_delivery_days': float(seller.average_delivery_days),
            'return_rate': float(seller.return_rate),
        }
        
        # Get improvement suggestions
        suggestions = predictor.get_improvement_suggestions(current_metrics, predicted)
        
        # Calculate impact
        impact = predicted['total_score'] - float(seller.performance_score)
        
        return JsonResponse({
            'success': True,
            'predicted_score': predicted['total_score'],
            'current_score': float(seller.performance_score),
            'impact': round(impact, 2),
            'status': predicted['status'],
            'breakdown': {
                'sales_score': predicted['sales_score'],
                'delivery_score': predicted['delivery_score'],
                'rating_score': predicted['rating_score'],
                'returns_penalty': predicted['returns_penalty'],
            },
            'weights': {
                'sales': predicted['sales_weight'],
                'delivery': predicted['delivery_weight'],
                'rating': predicted['rating_weight'],
                'returns': predicted['returns_weight'],
            },
            'breakdown_text': predicted['breakdown'],
            'suggestions': suggestions,
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in predict_performance_api: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
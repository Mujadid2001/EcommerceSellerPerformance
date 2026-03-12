"""
Admin interface views for comprehensive seller management.
Implements FR-02: View Seller List and FR-01: Input Seller Performance Data.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import json

from apps.performance.models import Seller, Order, CustomerFeedback
from apps.performance.services.import_export.import_service import DataImportService
from apps.performance.services.import_export.export_service import ExportService
from apps.ai_insights.models import PerformanceInsight, PredictiveAlert
from apps.ai_insights.services.ai_service import AIInsightService
from apps.authentication.middleware import admin_required


@staff_member_required
@admin_required
def admin_dashboard(request):
    """
    Main admin dashboard with system overview.
    Implements comprehensive admin functionality.
    """
    # Get system statistics
    total_sellers = Seller.objects.count()
    active_sellers = Seller.objects.filter(status=Seller.Status.ACTIVE).count()
    
    total_orders = Order.objects.count()
    recent_orders = Order.objects.filter(
        order_date__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    
    # Performance insights
    active_insights = PerformanceInsight.objects.filter(
        status=PerformanceInsight.Status.ACTIVE
    ).count()
    
    critical_alerts = PredictiveAlert.objects.filter(
        is_active=True,
        priority=PredictiveAlert.Priority.URGENT
    ).count()
    
    # Recent seller performance changes
    recent_performance_changes = Seller.objects.filter(
        updated_at__gte=timezone.now() - timezone.timedelta(hours=24)
    ).order_by('-updated_at')[:5]
    
    # Top/Bottom performers
    top_performers = Seller.objects.filter(
        status=Seller.Status.ACTIVE
    ).order_by('-performance_score')[:5]
    
    bottom_performers = Seller.objects.filter(
        status=Seller.Status.ACTIVE,
        total_orders__gt=0
    ).order_by('performance_score')[:5]
    
    context = {
        'stats': {
            'total_sellers': total_sellers,
            'active_sellers': active_sellers,
            'total_orders': total_orders,
            'recent_orders': recent_orders,
            'active_insights': active_insights,
            'critical_alerts': critical_alerts,
        },
        'recent_changes': recent_performance_changes,
        'top_performers': top_performers,
        'bottom_performers': bottom_performers,
    }
    
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
@admin_required
def seller_management(request):
    """
    Comprehensive seller management interface.
    Implements FR-02: View Seller List with advanced filtering and actions.
    """
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    score_min = request.GET.get('score_min', '')
    score_max = request.GET.get('score_max', '')
    sort_by = request.GET.get('sort', '-performance_score')
    
    # Build queryset
    queryset = Seller.objects.select_related('user').all()
    
    if search_query:
        queryset = queryset.filter(
            Q(business_name__icontains=search_query) |
            Q(business_registration__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if score_min:
        try:
            queryset = queryset.filter(performance_score__gte=float(score_min))
        except ValueError:
            pass
    
    if score_max:
        try:
            queryset = queryset.filter(performance_score__lte=float(score_max))
        except ValueError:
            pass
    
    # Apply sorting
    valid_sort_fields = [
        'business_name', '-business_name',
        'performance_score', '-performance_score',
        'created_at', '-created_at',
        'total_orders', '-total_orders',
        'average_rating', '-average_rating'
    ]
    
    if sort_by in valid_sort_fields:
        queryset = queryset.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    sellers = paginator.get_page(page_number)
    
    # Get status choices for filter
    status_choices = Seller.Status.choices
    
    context = {
        'sellers': sellers,
        'status_choices': status_choices,
        'current_filters': {
            'search': search_query,
            'status': status_filter,
            'score_min': score_min,
            'score_max': score_max,
            'sort': sort_by,
        },
        'total_count': queryset.count()
    }
    
    return render(request, 'admin/seller_management.html', context)


@staff_member_required
@admin_required
def seller_detail_admin(request, seller_id):
    """
    Detailed seller view for administrators with all performance data.
    """
    seller = get_object_or_404(Seller, id=seller_id)
    
    # Get comprehensive performance data
    orders = Order.objects.filter(seller=seller).order_by('-order_date')[:20]
    feedback = CustomerFeedback.objects.filter(
        order__seller=seller
    ).order_by('-created_at')[:10]
    
    # AI insights
    insights = PerformanceInsight.objects.filter(
        seller=seller,
        status=PerformanceInsight.Status.ACTIVE
    )
    
    alerts = PredictiveAlert.objects.filter(
        seller=seller,
        is_active=True
    )
    
    # Performance statistics
    total_orders = Order.objects.filter(seller=seller).count()
    completed_orders = Order.objects.filter(
        seller=seller, 
        status=Order.Status.DELIVERED
    ).count()
    
    returned_orders = Order.objects.filter(
        seller=seller, 
        is_returned=True
    ).count()
    
    avg_rating = CustomerFeedback.objects.filter(
        order__seller=seller
    ).aggregate(Avg('rating'))['rating__avg'] or 0
    
    context = {
        'seller': seller,
        'orders': orders,
        'feedback': feedback,
        'insights': insights,
        'alerts': alerts,
        'stats': {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'returned_orders': returned_orders,
            'avg_rating': round(avg_rating, 2),
            'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
            'return_rate': (returned_orders / total_orders * 100) if total_orders > 0 else 0,
        }
    }
    
    return render(request, 'admin/seller_detail.html', context)


@staff_member_required
@admin_required
def data_import_view(request):
    """
    Data import interface for administrators.
    Implements FR-01: Input Seller Performance Data.
    """
    if request.method == 'POST':
        return handle_data_import(request)
    
    # GET request - show import form
    import_service = DataImportService()
    
    context = {
        'supported_formats': import_service.SUPPORTED_FORMATS,
        'max_file_size_mb': import_service.MAX_FILE_SIZE / (1024 * 1024),
        'import_types': [
            ('orders', 'Orders'),
            ('sellers', 'Sellers'),
            ('feedback', 'Customer Feedback')
        ],
        'templates': {
            'orders': import_service.get_import_template('orders'),
            'sellers': import_service.get_import_template('sellers'),
            'feedback': import_service.get_import_template('feedback'),
        }
    }
    
    return render(request, 'admin/data_import.html', context)


@staff_member_required
@admin_required
@require_http_methods(["POST"])
def handle_data_import(request):
    """Handle file upload and data import processing."""
    try:
        uploaded_file = request.FILES.get('import_file')
        import_type = request.POST.get('import_type')
        
        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('admin:data_import')
        
        if not import_type:
            messages.error(request, 'Please select an import type.')
            return redirect('admin:data_import')
        
        # Validate file size
        if uploaded_file.size > DataImportService.MAX_FILE_SIZE:
            messages.error(request, 'File size exceeds maximum limit.')
            return redirect('admin:data_import')
        
        # Save uploaded file temporarily
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension not in DataImportService.SUPPORTED_FORMATS:
            messages.error(request, f'Unsupported file format: {file_extension}')
            return redirect('admin:data_import')
        
        # Save file
        file_path = default_storage.save(
            f'imports/{uploaded_file.name}',
            ContentFile(uploaded_file.read())
        )
        
        try:
            # Process import
            import_service = DataImportService()
            result = import_service.import_seller_data(
                file_path=default_storage.path(file_path),
                file_format=file_extension,
                user=request.user,
                import_type=import_type
            )
            
            if result['success']:
                stats = result['statistics']
                messages.success(
                    request,
                    f"Import completed! {stats['successful_imports']} records imported successfully. "
                    f"{stats['failed_imports']} records failed."
                )
                
                if stats['failed_imports'] > 0:
                    # Store error details in session for display
                    request.session['import_errors'] = stats['errors'][:10]  # Limit to 10 errors
                
            else:
                messages.error(request, f"Import failed: {result['error']}")
        
        finally:
            # Clean up temporary file
            default_storage.delete(file_path)
    
    except Exception as e:
        messages.error(request, f"Import processing failed: {str(e)}")
    
    return redirect('admin:data_import')


@staff_member_required
@admin_required
def data_export_view(request):
    """
    Data export interface for administrators.
    Implements FR-12: External Report Export.
    """
    export_service = ExportService()
    
    context = {
        'available_formats': export_service.get_available_export_formats(),
        'export_types': [
            ('sellers', 'Sellers Data'),
            ('orders', 'Orders Data'),
            ('performance_report', 'Full Performance Report')
        ]
    }
    
    return render(request, 'admin/data_export.html', context)


@staff_member_required
@admin_required
def generate_export(request):
    """Generate and download export file."""
    try:
        export_type = request.GET.get('type')
        export_format = request.GET.get('format')
        
        if not export_type or not export_format:
            messages.error(request, 'Invalid export parameters.')
            return redirect('admin:data_export')
        
        export_service = ExportService()
        
        if export_type == 'sellers' and export_format == 'csv':
            return export_service.export_sellers_csv(request.user)
        
        elif export_type == 'orders' and export_format == 'csv':
            return export_service.export_orders_csv(request.user)
        
        elif export_type == 'performance_report' and export_format == 'excel':
            return export_service.export_performance_report_excel(request.user)
        
        elif export_type == 'performance_report' and export_format == 'pdf':
            # For PDF, need to specify seller or generate summary
            seller_id = request.GET.get('seller_id')
            if seller_id:
                seller = get_object_or_404(Seller, id=seller_id)
                pdf_buffer = export_service.generate_seller_report_pdf(seller, request.user)
                
                response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
                filename = f"seller_report_{seller.business_name}_{timezone.now().strftime('%Y%m%d')}.pdf"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                messages.error(request, 'Please select a seller for PDF report generation.')
                return redirect('admin:data_export')
        
        else:
            messages.error(request, 'Invalid export combination.')
            return redirect('admin:data_export')
    
    except Exception as e:
        messages.error(request, f"Export failed: {str(e)}")
        return redirect('admin:data_export')


@staff_member_required
@admin_required
def ai_insights_dashboard(request):
    """
    AI insights dashboard for administrators.
    Shows AI-generated insights and alerts.
    """
    # Get active insights grouped by type
    insights_by_type = {}
    for insight_type, display_name in PerformanceInsight.InsightType.choices:
        insights_by_type[display_name] = PerformanceInsight.objects.filter(
            insight_type=insight_type,
            status=PerformanceInsight.Status.ACTIVE
        ).count()
    
    # Get critical alerts
    critical_alerts = PredictiveAlert.objects.filter(
        is_active=True,
        priority__in=[PredictiveAlert.Priority.HIGH, PredictiveAlert.Priority.URGENT]
    ).select_related('seller')[:10]
    
    # Get recent insights
    recent_insights = PerformanceInsight.objects.filter(
        status=PerformanceInsight.Status.ACTIVE
    ).select_related('seller').order_by('-created_at')[:15]
    
    # Performance trend summary
    trend_summary = {}
    for seller in Seller.objects.filter(status=Seller.Status.ACTIVE)[:10]:
        ai_service = AIInsightService()
        analysis = ai_service.analyze_seller_performance(seller)
        if 'trend_analysis' in analysis:
            trends = analysis['trend_analysis']
            trend_summary[seller.business_name] = {
                'revenue_trend': trends.get('revenue_trend', {}).get('direction', 'stable'),
                'order_trend': trends.get('order_trend', {}).get('direction', 'stable'),
                'return_trend': trends.get('return_rate_trend', {}).get('direction', 'stable'),
            }
    
    context = {
        'insights_by_type': insights_by_type,
        'critical_alerts': critical_alerts,
        'recent_insights': recent_insights,
        'trend_summary': trend_summary,
        'total_active_insights': sum(insights_by_type.values()),
        'total_critical_alerts': len(critical_alerts)
    }
    
    return render(request, 'admin/ai_insights_dashboard.html', context)


@staff_member_required
@admin_required
def trigger_ai_analysis(request, seller_id):
    """
    Manually trigger AI analysis for a specific seller.
    """
    try:
        seller = get_object_or_404(Seller, id=seller_id)
        ai_service = AIInsightService()
        
        # Run AI analysis
        analysis_result = ai_service.analyze_seller_performance(seller)
        
        if 'error' not in analysis_result:
            messages.success(
                request,
                f"AI analysis completed for {seller.business_name}. "
                f"Check the insights dashboard for results."
            )
        else:
            messages.error(
                request,
                f"AI analysis failed: {analysis_result['error']}"
            )
    
    except Exception as e:
        messages.error(request, f"Failed to trigger AI analysis: {str(e)}")
    
    return redirect('admin:seller_detail', seller_id=seller_id)


@staff_member_required
@admin_required
def system_health_check(request):
    """
    System health and performance monitoring dashboard.
    """
    # Database statistics
    db_stats = {
        'sellers': Seller.objects.count(),
        'orders': Order.objects.count(),
        'feedback': CustomerFeedback.objects.count(),
        'insights': PerformanceInsight.objects.count(),
        'alerts': PredictiveAlert.objects.filter(is_active=True).count()
    }
    
    # Performance metrics
    recent_orders = Order.objects.filter(
        order_date__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    
    avg_performance_score = Seller.objects.filter(
        status=Seller.Status.ACTIVE
    ).aggregate(Avg('performance_score'))['performance_score__avg'] or 0
    
    # System alerts
    system_alerts = []
    
    # Check for sellers with very low performance
    low_performance_sellers = Seller.objects.filter(
        status=Seller.Status.ACTIVE,
        performance_score__lt=30
    ).count()
    
    if low_performance_sellers > 0:
        system_alerts.append({
            'type': 'warning',
            'message': f"{low_performance_sellers} sellers have performance scores below 30"
        })
    
    # Check for high number of returns
    high_return_orders = Order.objects.filter(
        order_date__gte=timezone.now() - timezone.timedelta(days=7),
        is_returned=True
    ).count()
    
    if high_return_orders > recent_orders * 0.1:  # More than 10% returns
        system_alerts.append({
            'type': 'danger',
            'message': f"High return rate detected: {high_return_orders} returns in last 7 days"
        })
    
    context = {
        'db_stats': db_stats,
        'performance_metrics': {
            'recent_orders': recent_orders,
            'avg_performance_score': round(avg_performance_score, 2),
            'active_sellers': Seller.objects.filter(status=Seller.Status.ACTIVE).count()
        },
        'system_alerts': system_alerts,
    }
    
    return render(request, 'admin/system_health.html', context)
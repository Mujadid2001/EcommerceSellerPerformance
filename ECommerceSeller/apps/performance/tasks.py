"""
Celery tasks for Performance app.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import logging
import csv
from io import BytesIO

from apps.performance.models import Seller, Order
from apps.performance.services.performance_service import PerformanceCalculationService
from apps.performance.services.status_service import StatusAssignmentService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def recalculate_seller_performance(self, seller_id):
    """
    Recalculate performance score for a specific seller.
    """
    try:
        seller = Seller.objects.get(id=seller_id)
        calc_service = PerformanceCalculationService()
        status_service = StatusAssignmentService()
        
        # Calculate new performance score
        new_score = calc_service.calculate_performance_score(seller)
        seller.performance_score = new_score
        seller.last_evaluated_at = timezone.now()
        
        # Assign status based on score
        status_service.assign_status(seller)
        
        seller.save()
        
        logger.info(f"Performance recalculated for seller {seller_id}. New score: {new_score}")
        return {
            'seller_id': seller_id,
            'new_score': float(new_score),
            'status': seller.status,
        }
    except Seller.DoesNotExist:
        logger.error(f"Seller with id {seller_id} not found.")
        return {'status': 'failed', 'error': 'Seller not found'}
    except Exception as exc:
        logger.error(f"Error recalculating performance for seller {seller_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def recalculate_all_seller_performance():
    """
    Recalculate performance for all sellers.
    Runs daily via Celery Beat.
    """
    try:
        sellers = Seller.objects.all()
        count = 0
        
        for seller in sellers:
            recalculate_seller_performance.delay(seller.id)
            count += 1
        
        logger.info(f"Performance recalculation triggered for {count} sellers.")
        return {
            'sellers_count': count,
            'status': 'batch_started'
        }
    except Exception as e:
        logger.error(f"Error in batch seller performance recalculation: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def generate_daily_reports(time='00:00', sellers=None):
    """
    Generate performance reports for sellers.
    Runs daily via Celery Beat at specified time.
    """
    try:
        from apps.performance.models import Seller
        from datetime import datetime
        
        if sellers is None:
            sellers = Seller.objects.filter(status='active')
        else:
            sellers = Seller.objects.filter(id__in=sellers, status='active')
        
        report_date = timezone.now().date()
        report_count = 0
        
        for seller in sellers:
            # Generate report file
            export_report_for_seller.delay(seller.id, str(report_date))
            report_count += 1
        
        logger.info(f"Daily reports generation triggered for {report_count} sellers.")
        return {
            'reports_count': report_count,
            'date': str(report_date),
            'status': 'reports_queued'
        }
    except Exception as e:
        logger.error(f"Error generating daily reports: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def export_report_for_seller(seller_id, date_str=None):
    """
    Export performance report for a seller to CSV.
    """
    try:
        seller = Seller.objects.get(id=seller_id)
        
        if date_str is None:
            date_str = timezone.now().date().isoformat()
        
        # Generate CSV report
        orders = Order.objects.filter(seller=seller)
        
        if date_str:
            report_date = datetime.fromisoformat(date_str).date()
            orders = orders.filter(order_date__date=report_date)
        
        # Create CSV
        csv_file = BytesIO()
        writer = csv.writer(csv_file.getvalue().decode().split('\n'))
        
        # Write headers
        writer.writerow([
            'Order Number',
            'Customer Email',
            'Order Amount',
            'Status',
            'Delivery Days',
            'Order Date',
        ])
        
        # Write data
        for order in orders:
            writer.writerow([
                order.order_number,
                order.customer_email,
                order.order_amount,
                order.status,
                order.delivery_days,
                order.order_date,
            ])
        
        logger.info(f"Report exported for seller {seller_id} for date {date_str}")
        return {
            'seller_id': seller_id,
            'date': date_str,
            'orders_count': orders.count(),
            'status': 'exported'
        }
    except Exception as e:
        logger.error(f"Error exporting report for seller {seller_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def send_seller_performance_alert(seller_id):
    """
    Send performance alert email to seller.
    """
    try:
        seller = Seller.objects.get(id=seller_id)
        
        # Check if alert threshold reached
        if seller.performance_score < settings.AI_PERFORMANCE_ALERT_THRESHOLD:
            subject = f"Performance Alert: {seller.business_name}"
            context = {
                'seller': seller,
                'score': seller.performance_score,
                'threshold': settings.AI_PERFORMANCE_ALERT_THRESHOLD,
            }
            
            message = render_to_string('performance/alert_email.html', context)
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [seller.user.email],
                html_message=message,
                fail_silently=False,
            )
            
            logger.info(f"Performance alert sent to {seller.user.email}")
            return {'status': 'alert_sent', 'seller_id': seller_id}
        
        return {'status': 'no_alert_needed'}
    except Exception as e:
        logger.error(f"Error sending performance alert for seller {seller_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_old_orders(days=365):
    """
    Archive or delete old completed orders after X days.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        old_orders = Order.objects.filter(
            status='delivered',
            delivered_date__lt=cutoff_date
        )
        count, _ = old_orders.delete()
        
        logger.info(f"Cleaned up {count} old orders from database.")
        return {'status': 'cleaned', 'count': count}
    except Exception as e:
        logger.error(f"Error cleaning up old orders: {str(e)}")
        return {'status': 'error', 'message': str(e)}

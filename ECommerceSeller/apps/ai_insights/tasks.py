"""
Celery tasks for AI Insights app.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

from apps.performance.models import Seller
from apps.ai_insights.services.ai_service import AIInsightService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_ai_analysis_for_seller(self, seller_id):
    """
    Run AI analysis for a specific seller.
    """
    try:
        seller = Seller.objects.get(id=seller_id)
        ai_service = AIInsightService()
        insights = ai_service.analyze_seller_performance(seller)
        
        logger.info(f"AI analysis completed for seller {seller_id}. Generated {len(insights)} insights.")
        return {
            'seller_id': seller_id,
            'insights_count': len(insights),
            'status': 'success'
        }
    except Seller.DoesNotExist:
        logger.error(f"Seller with id {seller_id} not found.")
        return {'status': 'failed', 'error': 'Seller not found'}
    except Exception as exc:
        logger.error(f"Error running AI analysis for seller {seller_id}: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def run_ai_analysis_batch(batch_size=10):
    """
    Run AI analysis for all sellers in batches.
    Runs every hour via Celery Beat.
    """
    try:
        sellers = Seller.objects.filter(status='active').order_by('-performance_score')[:batch_size]
        
        for seller in sellers:
            run_ai_analysis_for_seller.delay(seller.id)
        
        logger.info(f"Batch AI analysis triggered for {sellers.count()} sellers.")
        return {
            'sellers_count': sellers.count(),
            'status': 'batch_started'
        }
    except Exception as e:
        logger.error(f"Error in batch AI analysis: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def generate_seller_insights_report(seller_id):
    """
    Generate comprehensive insights report for a seller.
    """
    try:
        seller = Seller.objects.get(id=seller_id)
        ai_service = AIInsightService()
        
        # Generate insights
        insights = ai_service.analyze_seller_performance(seller)
        
        # Send report via email
        subject = f"Performance Insights Report for {seller.business_name}"
        context = {
            'seller': seller,
            'insights': insights,
        }
        
        message = render_to_string('ai_insights/report_email.html', context)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [seller.user.email],
            html_message=message,
            fail_silently=False,
        )
        
        logger.info(f"Insights report sent to {seller.user.email}")
        return {'status': 'email_sent', 'seller_id': seller_id}
        
    except Exception as e:
        logger.error(f"Error generating insights report for seller {seller_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_old_insights(days=90):
    """
    Delete old AI insights after X days.
    """
    from apps.ai_insights.models import PerformanceInsight
    from datetime import timedelta
    from django.utils import timezone
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        old_insights = PerformanceInsight.objects.filter(created_at__lt=cutoff_date)
        count, _ = old_insights.delete()
        
        logger.info(f"Cleaned up {count} old AI insights from database.")
        return {'status': 'cleaned', 'count': count}
    except Exception as e:
        logger.error(f"Error cleaning up old insights: {str(e)}")
        return {'status': 'error', 'message': str(e)}

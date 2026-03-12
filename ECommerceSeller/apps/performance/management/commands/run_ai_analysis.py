"""
Management command to run complete AI analysis for all sellers.
Implements automated performance evaluation and AI insights generation.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from apps.performance.models import Seller
from apps.ai_insights.services.ai_service import AIInsightService
from apps.ai_insights.models import PerformanceInsight, PredictiveAlert
from apps.audit_trail.models import AuditEvent


class Command(BaseCommand):
    help = 'Run AI analysis for all active sellers and generate insights'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--seller-id',
            type=int,
            help='Run analysis for specific seller ID',
        )
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            help='Force refresh of cached analyses',
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['active', 'under_review', 'suspended'],
            default='active',
            help='Analyze sellers with specific status (default: active)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of sellers to process in each batch',
        )
    
    def handle(self, *args, **options):
        seller_id = options.get('seller_id')
        force_refresh = options.get('force_refresh')
        status = options.get('status')
        batch_size = options.get('batch_size')
        
        start_time = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting AI analysis at {start_time}')
        )
        
        try:
            # Build queryset
            if seller_id:
                queryset = Seller.objects.filter(id=seller_id)
                if not queryset.exists():
                    raise CommandError(f'Seller with ID {seller_id} does not exist')
            else:
                queryset = Seller.objects.filter(status=status)
            
            total_sellers = queryset.count()
            
            if total_sellers == 0:
                self.stdout.write(
                    self.style.WARNING('No sellers found matching criteria')
                )
                return
            
            self.stdout.write(f'Processing {total_sellers} sellers...')
            
            # Process sellers in batches
            processed_count = 0
            success_count = 0
            error_count = 0
            
            ai_service = AIInsightService()
            
            for i in range(0, total_sellers, batch_size):
                batch_sellers = queryset[i:i + batch_size]
                
                with transaction.atomic():
                    for seller in batch_sellers:
                        try:
                            self.stdout.write(
                                f'Processing seller: {seller.business_name} (ID: {seller.id})'
                            )
                            
                            # Clear cache if force refresh
                            if force_refresh:
                                from django.core.cache import cache
                                cache.delete(f"ai_analysis_{seller.id}")
                            
                            # Run AI analysis
                            analysis_result = ai_service.analyze_seller_performance(seller)
                            
                            if 'error' not in analysis_result:
                                success_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'✓ Analysis completed for {seller.business_name}')
                                )
                                
                                # Display key insights
                                if 'recommendations' in analysis_result:
                                    rec_count = len(analysis_result['recommendations'])
                                    self.stdout.write(f'  Generated {rec_count} recommendations')
                                
                                if 'overall_health_score' in analysis_result:
                                    health_score = analysis_result['overall_health_score']
                                    self.stdout.write(f'  Health score: {health_score:.1f}/100')
                            
                            else:
                                error_count += 1
                                self.stdout.write(
                                    self.style.ERROR(f'✗ Analysis failed for {seller.business_name}: {analysis_result["error"]}')
                                )
                        
                        except Exception as e:
                            error_count += 1
                            self.stdout.write(
                                self.style.ERROR(f'✗ Unexpected error for {seller.business_name}: {str(e)}')
                            )
                        
                        processed_count += 1
                        
                        # Progress indicator
                        if processed_count % 5 == 0:
                            progress = (processed_count / total_sellers) * 100
                            self.stdout.write(f'Progress: {processed_count}/{total_sellers} ({progress:.1f}%)')
                
                # Brief pause between batches to prevent resource exhaustion
                if i + batch_size < total_sellers:
                    import time
                    time.sleep(1)
            
            # Final summary
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('AI ANALYSIS COMPLETED'))
            self.stdout.write('='*50)
            self.stdout.write(f'Total sellers processed: {processed_count}')
            self.stdout.write(f'Successful analyses: {success_count}')
            self.stdout.write(f'Failed analyses: {error_count}')
            self.stdout.write(f'Duration: {duration:.2f} seconds')
            self.stdout.write(f'Average time per seller: {duration/processed_count:.2f} seconds')
            
            # Log to audit trail
            AuditEvent.log_event(
                event_type=AuditEvent.EventType.PERFORMANCE_CALCULATE,
                description=f'Bulk AI analysis completed: {success_count}/{processed_count} sellers processed',
                severity=AuditEvent.Severity.MEDIUM,
                total_processed=processed_count,
                successful=success_count,
                failed=error_count,
                duration_seconds=duration
            )
            
            # Generate insights summary
            recent_insights = PerformanceInsight.objects.filter(
                created_at__gte=start_time
            ).count()
            
            recent_alerts = PredictiveAlert.objects.filter(
                created_at__gte=start_time
            ).count()
            
            self.stdout.write(f'\nNew insights generated: {recent_insights}')
            self.stdout.write(f'New alerts generated: {recent_alerts}')
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\nOperation cancelled by user')
            )
        except Exception as e:
            raise CommandError(f'Command failed: {str(e)}')
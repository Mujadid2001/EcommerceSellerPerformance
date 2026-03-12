"""
Management command to evaluate all seller performances

Usage:
    python manage.py evaluate_sellers
    python manage.py evaluate_sellers --seller-id=123
    python manage.py evaluate_sellers --status=active
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.performance.models import Seller
from apps.performance.services import StatusAssignmentService


class Command(BaseCommand):
    help = 'Evaluate seller performance and update status'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--seller-id',
            type=int,
            help='Evaluate specific seller by ID',
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['active', 'under_review', 'suspended'],
            help='Evaluate sellers with specific status',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Evaluate all sellers',
        )
    
    def handle(self, *args, **options):
        seller_id = options.get('seller_id')
        status = options.get('status')
        evaluate_all = options.get('all')
        
        # Build queryset
        if seller_id:
            try:
                queryset = Seller.objects.filter(id=seller_id)
                if not queryset.exists():
                    raise CommandError(f'Seller with ID {seller_id} does not exist')
            except Seller.DoesNotExist:
                raise CommandError(f'Seller with ID {seller_id} does not exist')
        elif status:
            queryset = Seller.objects.filter(status=status)
        elif evaluate_all:
            queryset = Seller.objects.all()
        else:
            # Default: evaluate sellers that need evaluation
            queryset = Seller.objects.needs_evaluation()
        
        if not queryset.exists():
            self.stdout.write(self.style.WARNING('No sellers found to evaluate'))
            return
        
        self.stdout.write(f'Evaluating {queryset.count()} seller(s)...')
        
        # Evaluate sellers
        with transaction.atomic():
            summary = StatusAssignmentService.bulk_evaluate_sellers(queryset)
        
        # Output results
        self.stdout.write(self.style.SUCCESS(f'\nEvaluation Complete:'))
        self.stdout.write(f'  Total evaluated: {summary["total_evaluated"]}')
        self.stdout.write(f'  Status changes: {summary["status_changes"]}')
        self.stdout.write(f'\nStatus Distribution:')
        self.stdout.write(f'  Active: {summary["status_distribution"]["active"]}')
        self.stdout.write(f'  Under Review: {summary["status_distribution"]["under_review"]}')
        self.stdout.write(f'  Suspended: {summary["status_distribution"]["suspended"]}')
        
        if summary['errors']:
            self.stdout.write(self.style.ERROR(f'\nErrors: {len(summary["errors"])}'))
            for error in summary['errors']:
                self.stdout.write(self.style.ERROR(f'  Seller {error["seller_id"]}: {error["error"]}'))

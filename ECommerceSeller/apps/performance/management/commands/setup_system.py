"""
Setup and initialization script for E-Commerce Seller Performance System

Run this after initial setup to configure the application.
Usage: python manage.py setup_system
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup and initialize the performance evaluation system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-superuser',
            action='store_true',
            help='Skip superuser creation',
        )
        parser.add_argument(
            '--seed-data',
            action='store_true',
            help='Seed sample data after setup',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('E-Commerce Seller Performance System Setup'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Check database
        self.stdout.write('\n1. Checking database...')
        from django.db import connection
        try:
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS('   ✓ Database connection successful'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Database error: {e}'))
            return
        
        # Create superuser if needed
        if not options['skip_superuser']:
            self.stdout.write('\n2. Checking superuser...')
            if not User.objects.filter(is_superuser=True).exists():
                self.stdout.write('   Creating superuser...')
                try:
                    email = input('   Enter superuser email: ')
                    password = input('   Enter superuser password: ')
                    User.objects.create_superuser(
                        email=email,
                        password=password
                    )
                    self.stdout.write(self.style.SUCCESS('   ✓ Superuser created'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ✗ Error: {e}'))
            else:
                self.stdout.write(self.style.SUCCESS('   ✓ Superuser already exists'))
        
        # Check models
        self.stdout.write('\n3. Checking models...')
        from apps.performance.models import Seller, Order, CustomerFeedback
        
        sellers_count = Seller.objects.count()
        orders_count = Order.objects.count()
        feedback_count = CustomerFeedback.objects.count()
        
        self.stdout.write(f'   Sellers: {sellers_count}')
        self.stdout.write(f'   Orders: {orders_count}')
        self.stdout.write(f'   Feedback: {feedback_count}')
        
        # Seed data if requested
        if options['seed_data']:
            self.stdout.write('\n4. Seeding sample data...')
            from django.core.management import call_command
            call_command('seed_performance_data', sellers=5, orders=20)
            self.stdout.write(self.style.SUCCESS('   ✓ Sample data created'))
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Setup Complete!'))
        self.stdout.write('=' * 60)
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Run: python manage.py runserver')
        self.stdout.write('2. Visit: http://127.0.0.1:8000/')
        self.stdout.write('3. Admin: http://127.0.0.1:8000/admin/')
        self.stdout.write('4. API: http://127.0.0.1:8000/api/')
        self.stdout.write('\n')

"""
Comprehensive system setup command.
Sets up the complete E-Commerce Seller Performance system with sample data.
"""
import os
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import random
from datetime import timedelta

from apps.performance.models import Seller, Order, CustomerFeedback
from apps.ai_insights.models import AIModel

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup complete E-Commerce Seller Performance system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--with-sample-data',
            action='store_true',
            help='Include sample data generation',
        )
        parser.add_argument(
            '--sample-sellers',
            type=int,
            default=10,
            help='Number of sample sellers to create (default: 10)',
        )
        parser.add_argument(
            '--sample-orders-per-seller',
            type=int,
            default=50,
            help='Average number of orders per seller (default: 50)',
        )
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@ecommerce.com',
            help='Admin user email (default: admin@ecommerce.com)',
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123',
            help='Admin user password (default: admin123)',
        )
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Skip running migrations',
        )
        parser.add_argument(
            '--force-reset',
            action='store_true',
            help='Reset database before setup (WARNING: This will delete all data)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting E-Commerce Seller Performance System Setup')
        )
        
        try:
            # Force reset if requested (WARNING)
            if options['force_reset']:
                self.stdout.write(
                    self.style.WARNING('⚠️  Force reset requested - This will delete ALL data!')
                )
                confirm = input('Are you sure you want to continue? Type "yes" to confirm: ')
                if confirm.lower() != 'yes':
                    self.stdout.write(self.style.ERROR('Setup cancelled.'))
                    return
                
                self.stdout.write('Resetting database...')
                self._reset_database()
            
            # Step 1: Run migrations
            if not options['skip_migrations']:
                self.stdout.write('📦 Running migrations...')
                call_command('makemigrations', verbosity=0)
                call_command('migrate', verbosity=0)
                self.stdout.write(self.style.SUCCESS('✓ Migrations completed'))
            
            # Step 2: Create superuser
            self.stdout.write('👤 Setting up admin user...')
            admin_user = self._create_admin_user(
                options['admin_email'], 
                options['admin_password']
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Admin user created: {admin_user.email}')
            )
            
            # Step 3: Initialize AI models
            self.stdout.write('🧠 Initializing AI models...')
            self._initialize_ai_models()
            self.stdout.write(self.style.SUCCESS('✓ AI models initialized'))
            
            # Step 4: Create sample data if requested
            if options['with_sample_data']:
                self.stdout.write('🎲 Generating sample data...')
                self._create_sample_data(
                    num_sellers=options['sample_sellers'],
                    orders_per_seller=options['sample_orders_per_seller']
                )
                self.stdout.write(self.style.SUCCESS('✓ Sample data generated'))
            
            # Step 5: Run initial performance calculations
            self.stdout.write('📊 Running initial performance calculations...')
            call_command('evaluate_sellers', '--all', verbosity=0)
            self.stdout.write(self.style.SUCCESS('✓ Performance calculations completed'))
            
            # Step 6: Generate initial AI insights
            if options['with_sample_data']:
                self.stdout.write('🔮 Generating AI insights...')
                call_command('run_ai_analysis', '--batch-size', '3', verbosity=0)
                self.stdout.write(self.style.SUCCESS('✓ AI insights generated'))
            
            # Step 7: Setup complete
            self._display_completion_summary(admin_user, options)
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n⏸️  Setup interrupted by user')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Setup failed: {str(e)}')
            )
            raise CommandError(f'System setup failed: {str(e)}')
    
    def _reset_database(self):
        """Reset database by deleting all data (DANGEROUS!)"""
        from django.core.management import call_command
        
        # Delete all data
        for model in [Order, CustomerFeedback, Seller, User]:
            model.objects.all().delete()
        
        # Reset migrations
        call_command('migrate', 'performance', 'zero', verbosity=0)
        call_command('migrate', 'authentication', 'zero', verbosity=0)
        call_command('migrate', 'audit_trail', 'zero', verbosity=0)
        call_command('migrate', 'ai_insights', 'zero', verbosity=0)
    
    def _create_admin_user(self, email, password):
        """Create or get admin user"""
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f'Admin user already exists: {email}')
            return user
        except User.DoesNotExist:
            user = User.objects.create_superuser(
                email=email,
                password=password,
                first_name='System',
                last_name='Administrator',
                role=User.Role.ADMIN
            )
            return user
    
    def _initialize_ai_models(self):
        """Initialize AI model configurations"""
        ai_models_config = [
            {
                'name': 'PerformancePredictor',
                'version': '1.0',
                'model_type': AIModel.ModelType.PERFORMANCE_PREDICTOR,
                'status': AIModel.Status.ACTIVE,
                'config': {
                    'algorithm': 'linear_regression',
                    'features': ['delivery_days', 'return_rate', 'order_volume'],
                    'prediction_horizon_days': 30
                },
                'accuracy': Decimal('82.5'),
                'precision': Decimal('78.3'),
                'recall': Decimal('85.7')
            },
            {
                'name': 'TrendAnalyzer',
                'version': '1.0',
                'model_type': AIModel.ModelType.TREND_ANALYZER,
                'status': AIModel.Status.ACTIVE,
                'config': {
                    'algorithm': 'time_series_analysis',
                    'window_size_days': 30,
                    'trend_threshold': 0.1
                },
                'accuracy': Decimal('75.2'),
                'precision': Decimal('72.1'),
                'recall': Decimal('79.8')
            },
            {
                'name': 'AnomalyDetector',
                'version': '1.0',
                'model_type': AIModel.ModelType.ANOMALY_DETECTOR,
                'status': AIModel.Status.ACTIVE,
                'config': {
                    'algorithm': 'statistical_outlier',
                    'std_threshold': 2.0,
                    'min_data_points': 10
                },
                'accuracy': Decimal('88.9'),
                'precision': Decimal('85.4'),
                'recall': Decimal('91.2')
            },
            {
                'name': 'RecommendationEngine',
                'version': '1.0',
                'model_type': AIModel.ModelType.RECOMMENDATION_ENGINE,
                'status': AIModel.Status.ACTIVE,
                'config': {
                    'algorithm': 'rule_based',
                    'confidence_threshold': 0.7,
                    'max_recommendations': 5
                },
                'accuracy': Decimal('79.6'),
                'precision': Decimal('76.8'),
                'recall': Decimal('83.1')
            }
        ]
        
        for model_config in ai_models_config:
            ai_model, created = AIModel.objects.get_or_create(
                name=model_config['name'],
                version=model_config['version'],
                defaults=model_config
            )
            
            if created:
                ai_model.last_trained_at = timezone.now()
                ai_model.save()
    
    def _create_sample_data(self, num_sellers, orders_per_seller):
        """Generate comprehensive sample data"""
        
        # Sample business names and data
        business_names = [
            'TechGadgets Pro', 'Fashion Forward', 'Home & Garden Plus', 'Sports Central',
            'Electronic World', 'Beauty Essentials', 'Book Haven', 'Auto Parts Direct',
            'Kitchen Masters', 'Gaming Universe', 'Fitness First', 'Pet Paradise',
            'Art Supplies Co', 'Music Store', 'Tools & Hardware'
        ]
        
        sample_domains = [
            'techgadgets.com', 'fashionforward.com', 'homegardenplus.com',
            'sportscentral.com', 'electronicworld.com', 'beautyessentials.com',
            'bookhaven.com', 'autopartsdirect.com', 'kitchenmasters.com',
            'gaminguniv.com', 'fitnessfirst.com', 'petparadise.com',
            'artsupplies.com', 'musicstore.com', 'toolshardware.com'
        ]
        
        # Create sellers
        sellers = []
        for i in range(min(num_sellers, len(business_names))):
            business_name = business_names[i]
            domain = sample_domains[i]
            email = f'seller{i+1}@{domain}'
            
            # Create user
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=email,
                    password='seller123',
                    first_name=f'Seller',
                    last_name=f'{i+1}',
                    role=User.Role.SELLER,
                    is_verified=True,
                    is_approved=True
                )
            
            # Create seller profile
            seller, created = Seller.objects.get_or_create(
                business_registration=f'BUS{1000+i}',
                defaults={
                    'user': user,
                    'business_name': business_name,
                    'description': f'Professional {business_name.lower()} with quality products and excellent service.',
                    'status': Seller.Status.ACTIVE
                }
            )
            
            sellers.append(seller)
            
            if created:
                self.stdout.write(f'  Created seller: {business_name}')
        
        # Create orders and feedback
        customer_emails = [
            f'customer{i}@example.com' for i in range(1, 101)
        ]
        
        order_statuses = [
            Order.Status.DELIVERED,
            Order.Status.DELIVERED,
            Order.Status.DELIVERED,
            Order.Status.SHIPPED,
            Order.Status.PROCESSING,
            Order.Status.RETURNED
        ]
        
        feedback_comments = [
            'Great product, fast shipping!',
            'Excellent quality, highly recommended.',
            'Good value for money.',
            'Fast delivery, well packaged.',
            'Product as described, satisfied.',
            'Could be better, but acceptable.',
            'Outstanding service!',
            'Will buy again.',
            'Good customer support.',
            'Product exceeded expectations.'
        ]
        
        total_orders_created = 0
        
        for seller in sellers:
            # Generate random number of orders around the average
            num_orders = random.randint(
                int(orders_per_seller * 0.5), 
                int(orders_per_seller * 1.5)
            )
            
            for j in range(num_orders):
                # Generate order
                order_date = timezone.now() - timedelta(
                    days=random.randint(1, 365)
                )
                
                order = Order.objects.create(
                    seller=seller,
                    order_number=f'ORD-{seller.id}-{j+1:04d}',
                    customer_email=random.choice(customer_emails),
                    order_amount=Decimal(str(random.uniform(10.00, 500.00))),
                    order_date=order_date,
                    status=random.choice(order_statuses)
                )
                
                # Set delivery dates for delivered orders
                if order.status == Order.Status.DELIVERED:
                    days_to_deliver = random.randint(1, 14)
                    order.shipped_date = order_date + timedelta(days=random.randint(1, 3))
                    order.delivered_date = order.shipped_date + timedelta(days=days_to_deliver)
                    order.delivery_days = days_to_deliver
                    
                    # Occasionally mark as returned
                    if random.random() < 0.05:  # 5% return rate
                        order.is_returned = True
                        order.return_date = order.delivered_date + timedelta(days=random.randint(1, 30))
                        order.return_reason = random.choice([
                            'Product defect', 'Not as described', 'Wrong size', 
                            'Changed mind', 'Damaged in shipping'
                        ])
                    
                    order.save()
                    
                    # Generate feedback for some delivered orders
                    if random.random() < 0.7:  # 70% of delivered orders get feedback
                        rating = random.choices(
                            [1, 2, 3, 4, 5],
                            weights=[2, 3, 10, 35, 50],  # Weighted towards higher ratings
                            k=1
                        )[0]
                        
                        CustomerFeedback.objects.create(
                            order=order,
                            customer_email=order.customer_email,
                            rating=rating,
                            comment=random.choice(feedback_comments) if rating >= 4 else 'Could be improved.',
                            created_at=order.delivered_date + timedelta(days=random.randint(0, 7))
                        )
                
                total_orders_created += 1
                
                # Progress indicator
                if total_orders_created % 100 == 0:
                    self.stdout.write(f'    Generated {total_orders_created} orders...')
        
        self.stdout.write(f'  Total orders created: {total_orders_created}')
        
        # Update seller performance metrics
        from apps.performance.services.performance_service import PerformanceCalculationService
        
        for seller in sellers:
            service = PerformanceCalculationService(seller)
            score = service.calculate_performance_score()
            
            # Update seller metrics
            orders = Order.objects.filter(seller=seller)
            seller.total_orders = orders.count()
            seller.total_sales_volume = sum(order.order_amount for order in orders)
            seller.performance_score = score
            
            # Calculate other metrics
            delivered_orders = orders.filter(status=Order.Status.DELIVERED)
            if delivered_orders:
                seller.average_delivery_days = sum(
                    order.delivery_days for order in delivered_orders if order.delivery_days
                ) / delivered_orders.count()
                
                feedback = CustomerFeedback.objects.filter(order__seller=seller)
                if feedback:
                    seller.average_rating = sum(f.rating for f in feedback) / feedback.count()
                
                returned_orders = orders.filter(is_returned=True).count()
                seller.return_rate = (returned_orders / orders.count()) * 100
            
            seller.save()
    
    def _display_completion_summary(self, admin_user, options):
        """Display setup completion summary"""
        
        # System statistics
        total_users = User.objects.count()
        total_sellers = Seller.objects.count()
        total_orders = Order.objects.count()
        total_feedback = CustomerFeedback.objects.count()
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS('🎉 E-COMMERCE SELLER PERFORMANCE SYSTEM SETUP COMPLETE!')
        )
        self.stdout.write('='*60)
        
        self.stdout.write(f'📊 SYSTEM STATISTICS:')
        self.stdout.write(f'   • Total Users: {total_users}')
        self.stdout.write(f'   • Total Sellers: {total_sellers}')
        self.stdout.write(f'   • Total Orders: {total_orders}')
        self.stdout.write(f'   • Total Feedback: {total_feedback}')
        
        self.stdout.write(f'\n🔐 ADMIN ACCESS:')
        self.stdout.write(f'   • Email: {admin_user.email}')
        self.stdout.write(f'   • Password: {options["admin_password"]}')
        
        self.stdout.write(f'\n🌐 ACCESS POINTS:')
        self.stdout.write(f'   • Homepage: http://127.0.0.1:8000/')
        self.stdout.write(f'   • Admin Dashboard: http://127.0.0.1:8000/admin-dashboard/')
        self.stdout.write(f'   • Django Admin: http://127.0.0.1:8000/admin/')
        self.stdout.write(f'   • API Root: http://127.0.0.1:8000/marketplace/api/')
        self.stdout.write(f'   • Seller Dashboard: http://127.0.0.1:8000/marketplace/dashboard/')
        
        self.stdout.write(f'\n🚀 NEXT STEPS:')
        self.stdout.write(f'   1. Start the development server: python manage.py runserver')
        self.stdout.write(f'   2. Visit the admin dashboard to explore features')
        self.stdout.write(f'   3. Test seller functionalities with sample accounts')
        self.stdout.write(f'   4. Review AI insights and recommendations')
        
        if options['with_sample_data']:
            self.stdout.write(f'\n🧪 SAMPLE DATA INCLUDED:')
            self.stdout.write(f'   • Sample seller credentials: seller1@techgadgets.com / seller123')
            self.stdout.write(f'   • All sellers have realistic order and feedback data')
            self.stdout.write(f'   • AI insights have been generated automatically')
        
        self.stdout.write('\n' + '='*60)
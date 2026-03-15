"""
Management command to populate the database with sample data.
Populates all tables: Users, Sellers, Orders, Feedback, AI Insights, and Audit Events.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random
from decimal import Decimal
import json

from apps.authentication.models import User
from apps.performance.models import Seller, Order, CustomerFeedback
from apps.ai_insights.models import PerformanceInsight
from apps.audit_trail.models import AuditEvent

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate the database with sample data for development across all tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create (default: 10)'
        )
        parser.add_argument(
            '--orders',
            type=int,
            default=50,
            help='Number of orders to create (default: 50)'
        )
        parser.add_argument(
            '--insights',
            type=int,
            default=30,
            help='Number of AI insights to create (default: 30)'
        )
        parser.add_argument(
            '--audit-events',
            type=int,
            default=100,
            help='Number of audit events to create (default: 100)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting comprehensive database population...'))

        # Clear existing data (optional)
        if input("Clear existing data? (y/N): ").lower() == 'y':
            self.clear_data()

        # Create sample data
        users_count = options['users']
        orders_count = options['orders']
        insights_count = options['insights']
        audit_events_count = options['audit_events']

        admin_user = self.create_admin_user()
        regular_users = self.create_regular_users()
        sellers = self.create_sellers(users_count)
        orders = self.create_orders(sellers, orders_count)
        feedback_count = self.create_feedback(orders)
        insights_count_created = self.create_ai_insights(sellers, insights_count)
        audit_count = self.create_audit_events(admin_user, sellers, audit_events_count)

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Database populated successfully!\n'
                f'   - Created {len(sellers)} sellers\n'
                f'   - Created {len(orders)} orders\n'
                f'   - Created {feedback_count} feedback entries\n'
                f'   - Created {insights_count_created} AI insights\n'
                f'   - Created {audit_count} audit events\n'
                f'   - Admin user: admin@example.com / admin123'
            )
        )

    def clear_data(self):
        """Clear existing data"""
        self.stdout.write('🧹 Clearing existing data...')
        PerformanceInsight.objects.all().delete()
        AuditEvent.objects.all().delete()
        CustomerFeedback.objects.all().delete()
        Order.objects.all().delete()
        Seller.objects.all().delete()
        # Clear all non-admin users
        User.objects.filter(role__in=[User.Role.USER, User.Role.SELLER]).delete()
        self.stdout.write(self.style.WARNING('   Data cleared!'))

    def create_admin_user(self):
        """Create admin user"""
        try:
            admin = User.objects.get(email='admin@example.com')
            self.stdout.write(f'👤 Admin user already exists: {admin.email}')
        except User.DoesNotExist:
            admin = User.objects.create_superuser(
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(f'👤 Created admin user: {admin.email}')
        
        return admin

    def create_regular_users(self):
        """Create regular non-seller users"""
        self.stdout.write('👥 Creating regular users...')
        
        regular_users = []
        for i in range(3):
            email = f'user{i+1}@example.com'
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=email,
                    password='password123',
                    first_name=f'User{i+1}',
                    last_name='Regular',
                    phone=f'+1234567{900+i}'
                )
                user.role = User.Role.USER
                user.is_verified = True
                user.is_approved = True
                user.save()
                regular_users.append(user)
        
        self.stdout.write(f'   ✅ Created {len(regular_users)} regular users')
        return regular_users

    def create_sellers(self, count):
        """Create sample sellers"""
        self.stdout.write(f'👥 Creating {count} sellers...')
        
        business_names = [
            'TechGadgets Pro', 'Fashion Forward', 'Home & Garden Plus', 
            'Sports Central', 'Book Haven', 'Kitchen Masters', 
            'Auto Parts Direct', 'Pet Paradise', 'Beauty Basics',
            'Electronics Zone', 'Craft Corner', 'Outdoor Adventures',
            'Music Store', 'Toy Kingdom', 'Health & Wellness'
        ]
        
        descriptions = [
            'High-quality products with excellent customer service',
            'Premium brands at competitive prices',
            'Your one-stop shop for all needs',
            'Fast shipping and hassle-free returns',
            'Trusted by thousands of customers',
            'Quality guaranteed on every purchase'
        ]
        
        sellers = []
        
        for i in range(min(count, len(business_names))):
            # Create user
            email = f'seller{i+1}@example.com'
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=email,
                    password='password123',
                    first_name=f'Seller{i+1}',
                    last_name='User',
                    phone=f'+1234567890{i}',
                    role=User.Role.SELLER
                )
                user.is_verified = True
                user.is_approved = True
                user.save()
            
            # Create seller profile
            seller, seller_created = Seller.objects.get_or_create(
                user=user,
                defaults={
                    'business_name': business_names[i],
                    'business_registration': f'BR{1000 + i}',
                    'description': random.choice(descriptions),
                    'status': 'active'
                }
            )
            
            sellers.append(seller)
            
        self.stdout.write(f'   ✅ Created {len(sellers)} sellers')
        return sellers

    def create_orders(self, sellers, count):
        """Create sample orders"""
        self.stdout.write(f'📦 Creating {count} orders...')
        
        statuses = [
            ('pending', 20),
            ('processing', 25), 
            ('shipped', 20),
            ('delivered', 30),
            ('cancelled', 3),
            ('returned', 2)
        ]
        
        # Weighted status selection
        status_choices = []
        for status, weight in statuses:
            status_choices.extend([status] * weight)
        
        customers = [
            'john.doe@email.com', 'jane.smith@email.com', 'bob.johnson@email.com',
            'alice.wilson@email.com', 'charlie.brown@email.com', 'diana.davis@email.com',
            'eve.miller@email.com', 'frank.garcia@email.com', 'grace.martinez@email.com',
            'henry.anderson@email.com', 'ivy.taylor@email.com', 'jack.thomas@email.com'
        ]
        
        orders = []
        
        for i in range(count):
            seller = random.choice(sellers)
            customer = random.choice(customers)
            
            # Random date within last 90 days
            days_ago = random.randint(0, 90)
            order_date = timezone.now() - timedelta(days=days_ago)
            
            # Random order amount between $10 and $1000
            amount = Decimal(str(round(random.uniform(10.00, 1000.00), 2)))
            
            status = random.choice(status_choices)
            
            # Create dates based on status
            shipped_date = None
            delivered_date = None
            
            if status in ['shipped', 'delivered', 'returned']:
                shipped_date = order_date + timedelta(days=random.randint(1, 3))
                
            if status in ['delivered', 'returned']:
                delivered_date = shipped_date + timedelta(days=random.randint(1, 7))
            
            # Generate order number
            order_number = f"{seller.business_name[:3].upper()}-{1000 + i}"
            
            order = Order(
                seller=seller,
                order_number=order_number,
                customer_email=customer,
                order_amount=amount,
                order_date=order_date,
                shipped_date=shipped_date,
                delivered_date=delivered_date,
                status=status,
                return_reason='Product not as expected' if status == 'returned' else ''
            )
            # Skip validation during data seeding
            order.save(skip_validation=True)
            
            orders.append(order)
            
        self.stdout.write(f'   ✅ Created {len(orders)} orders')
        return orders

    def create_feedback(self, orders):
        """Create sample customer feedback"""
        self.stdout.write('⭐ Creating customer feedback...')
        
        positive_comments = [
            'Excellent product quality and fast shipping!',
            'Great seller, will buy again!',
            'Product exactly as described, very satisfied.',
            'Quick delivery and good communication.',
            'High quality item, exceeded expectations!'
        ]
        
        neutral_comments = [
            'Product is okay, nothing special.',
            'Average quality for the price.',
            'Delivery was a bit slow but item is fine.',
            'Product works as expected.'
        ]
        
        negative_comments = [
            'Product quality was disappointing.',
            'Took too long to ship.',
            'Not exactly as described in listing.',
            'Had some issues with the product.'
        ]
        
        feedback_count = 0
        
        # Create feedback for some delivered orders
        delivered_orders = [o for o in orders if o.status == 'delivered']
        
        for order in delivered_orders[:len(delivered_orders)//2]:  # 50% of delivered orders get feedback
            # Rating distribution: mostly positive
            rating_weights = [1, 2, 5, 15, 25]  # 1-star to 5-star weights
            rating = random.choices(range(1, 6), weights=rating_weights)[0]
            
            # Select comment based on rating
            if rating >= 4:
                comment = random.choice(positive_comments)
            elif rating == 3:
                comment = random.choice(neutral_comments)
            else:
                comment = random.choice(negative_comments)
            
            # Feedback date after delivery
            feedback_date = order.delivered_date + timedelta(days=random.randint(1, 14))
            
            feedback = CustomerFeedback.objects.create(
                seller=order.seller,
                order=order,
                rating=rating,
                comment=comment
            )
            # Set custom created_at
            feedback.created_at = feedback_date
            feedback.save()
            
            feedback_count += 1
            
        self.stdout.write(f'   ✅ Created {feedback_count} feedback entries')
        return feedback_count

    def create_ai_insights(self, sellers, count):
        """Create sample AI performance insights"""
        self.stdout.write(f'🤖 Creating {count} AI insights...')
        
        insight_types = [
            PerformanceInsight.InsightType.TREND_ANALYSIS,
            PerformanceInsight.InsightType.PERFORMANCE_ALERT,
            PerformanceInsight.InsightType.RECOMMENDATION,
            PerformanceInsight.InsightType.PREDICTION,
            PerformanceInsight.InsightType.RANKING_CHANGE,
            PerformanceInsight.InsightType.BENCHMARK_COMPARISON,
        ]
        
        severities = [
            PerformanceInsight.Severity.INFO,
            PerformanceInsight.Severity.LOW,
            PerformanceInsight.Severity.MEDIUM,
            PerformanceInsight.Severity.HIGH,
        ]
        
        statuses = [
            PerformanceInsight.Status.ACTIVE,
            PerformanceInsight.Status.ACKNOWLEDGED,
        ]
        
        insight_titles = {
            'trend_analysis': [
                'Sales trend showing steady growth',
                'Customer satisfaction trending upward',
                'Delivery performance improving',
                'Return rate declining'
            ],
            'performance_alert': [
                'Performance score increased',
                'Excellent customer feedback received',
                'Order volume peak detected',
                'Rating improvement confirmed'
            ],
            'recommendation': [
                'Consider expanding product categories',
                'Improve communication during peak hours',
                'Implement quality assurance process',
                'Review pricing strategy'
            ],
            'prediction': [
                'Predicted sales growth for next quarter',
                'Expected peak season in 30 days',
                'Forecasted performance improvement',
                'Customer retention prediction'
            ],
            'ranking_change': [
                'Rank improved to top 10%',
                'Performance rank increased by 5 positions',
                'Promoted to premium seller status',
                'Category ranking improved'
            ],
            'benchmark_comparison': [
                'Outperforming category average',
                'Matching industry standards',
                'Above average delivery speed',
                'Customer satisfaction at 95th percentile'
            ]
        }
        
        insights_created = 0
        
        for i in range(count):
            seller = random.choice(sellers)
            insight_type = random.choice(insight_types)
            
            title = random.choice(insight_titles.get(insight_type, ['AI Insight']))
            
            descriptions = {
                'trend_analysis': f'Our AI analysis detected a {random.randint(5, 20)}% improvement in seller metrics over the last month.',
                'performance_alert': f'Seller performance has reached a new milestone with {random.randint(85, 98)} performance score.',
                'recommendation': f'Based on historical data, we recommend taking action to optimize seller operations.',
                'prediction': f'Predictive analytics suggest {random.randint(10, 50)}% growth potential in the next period.',
                'ranking_change': f'Seller rank has been updated based on latest performance metrics.',
                'benchmark_comparison': f'Seller is performing better than {random.randint(70, 95)}% of similar sellers in the category.'
            }
            
            insights = PerformanceInsight.objects.create(
                seller=seller,
                insight_type=insight_type,
                severity=random.choice(severities),
                status=random.choice(statuses),
                title=title,
                description=descriptions.get(insight_type, 'AI-generated insight'),
                recommendation=f'Action items based on {insight_type}: Monitor performance, Maintain quality standards.',
                confidence_score=Decimal(str(round(random.uniform(70.0, 99.9), 2))),
                analysis_data={
                    'metric': f'metric_{i}',
                    'value': round(random.uniform(50, 100), 2),
                    'trend': random.choice(['up', 'down', 'stable']),
                    'period_days': 30
                },
                predicted_value=Decimal(str(round(random.uniform(50, 100), 2))) if insight_type == 'prediction' else None,
                prediction_timeframe_days=30 if insight_type == 'prediction' else None,
                expires_at=timezone.now() + timedelta(days=random.randint(7, 90))
            )
            
            insights_created += 1
        
        self.stdout.write(f'   ✅ Created {insights_created} AI insights')
        return insights_created

    def create_audit_events(self, admin_user, sellers, count):
        """Create sample audit events"""
        self.stdout.write(f'📋 Creating {count} audit events...')
        
        event_types = [
            AuditEvent.EventType.LOGIN,
            AuditEvent.EventType.LOGOUT,
            AuditEvent.EventType.CREATE,
            AuditEvent.EventType.UPDATE,
            AuditEvent.EventType.VIEW,
            AuditEvent.EventType.REPORT_GENERATE,
            AuditEvent.EventType.STATUS_CHANGE,
            AuditEvent.EventType.PERFORMANCE_CALCULATE,
            AuditEvent.EventType.SELLER_EVALUATE,
            AuditEvent.EventType.PASSWORD_CHANGE,
        ]
        
        severities = [
            AuditEvent.Severity.LOW,
            AuditEvent.Severity.MEDIUM,
            AuditEvent.Severity.HIGH,
        ]
        
        request_paths = [
            '/marketplace/dashboard/',
            '/api/sellers/',
            '/api/orders/',
            '/api/performance/',
            '/admin/',
            '/api/insights/',
            '/exports/',
        ]
        
        request_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        
        all_users = list(User.objects.filter(is_active=True)[:20])
        
        events_created = 0
        
        for i in range(count):
            user = random.choice(all_users) if all_users else admin_user
            event_type = random.choice(event_types)
            
            descriptions = {
                'login': f'User {user.email} logged in successfully',
                'logout': f'User {user.email} logged out',
                'create': f'Created new record in the system',
                'update': f'Updated seller performance data',
                'view': f'Viewed performance dashboard',
                'report_generate': f'Generated performance report',
                'status_change': f'Changed seller status',
                'performance_calculate': f'Calculated seller performance metrics',
                'seller_evaluate': f'Evaluated seller performance',
                'password_change': f'User changed password',
            }
            
            # Random date within last 30 days
            days_ago = random.randint(0, 30)
            event_time = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
            audit_event = AuditEvent.objects.create(
                event_type=event_type,
                severity=random.choice(severities),
                user=user,
                user_email=user.email,
                ip_address=f'{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                request_path=random.choice(request_paths),
                request_method=random.choice(request_methods),
                description=descriptions.get(event_type, 'System event'),
                details={
                    'action': event_type,
                    'resource_type': random.choice(['seller', 'order', 'user', 'performance']),
                    'resource_id': random.randint(1, 100),
                    'timestamp': event_time.isoformat()
                },
                success=random.choice([True, True, True, False]),  # 75% success rate
                timestamp=event_time
            )
            
            events_created += 1
        
        self.stdout.write(f'   ✅ Created {events_created} audit events')
        return events_created
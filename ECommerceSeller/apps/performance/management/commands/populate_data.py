"""
Management command to populate the database with sample data.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random
from decimal import Decimal

from apps.authentication.models import User
from apps.performance.models import Seller, Order, CustomerFeedback

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate the database with sample data for development'

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

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting database population...'))

        # Clear existing data (optional)
        if input("Clear existing data? (y/N): ").lower() == 'y':
            self.clear_data()

        # Create sample data
        users_count = options['users']
        orders_count = options['orders']

        self.create_admin_user()
        sellers = self.create_sellers(users_count)
        orders = self.create_orders(sellers, orders_count)
        self.create_feedback(orders)

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Database populated successfully!\n'
                f'   - Created {len(sellers)} sellers\n'
                f'   - Created {len(orders)} orders\n'
                f'   - Created feedback entries\n'
                f'   - Admin user: admin@example.com / admin123'
            )
        )

    def clear_data(self):
        """Clear existing data"""
        self.stdout.write('🧹 Clearing existing data...')
        CustomerFeedback.objects.all().delete()
        Order.objects.all().delete()
        Seller.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING('   Data cleared!'))

    def create_admin_user(self):
        """Create admin user"""
        if not User.objects.filter(email='admin@example.com').exists():
            admin = User.objects.create_user(
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User',
                role=User.Role.ADMIN,
                is_staff=True,
                is_superuser=True,
                is_active=True,
                is_verified=True,
                is_approved=True
            )
            self.stdout.write(f'👤 Created admin user: {admin.email}')

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
            user = User.objects.create_user(
                email=email,
                password='password123',
                first_name=f'Seller{i+1}',
                last_name='User',
                role=User.Role.SELLER,
                phone=f'+1234567890{i}',
                is_active=True,
                is_verified=True,
                is_approved=True
            )
            
            # Create seller profile
            seller = Seller.objects.create(
                user=user,
                business_name=business_names[i],
                business_registration=f'BR{1000 + i}',
                description=random.choice(descriptions),
                status='active'
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
            
            order = Order.objects.create(
                seller=seller,
                order_number=order_number,
                customer_email=customer,
                order_amount=amount,
                order_date=order_date,
                shipped_date=shipped_date,
                delivered_date=delivered_date,
                status=status,
                return_reason='Product not as expected' if status == 'returned' else None
            )
            
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

    def style_text(self, text, style):
        """Helper method for colored output"""
        styles = {
            'success': '\033[92m',
            'warning': '\033[93m',
            'error': '\033[91m',
            'info': '\033[94m',
            'end': '\033[0m'
        }
        return f"{styles.get(style, '')}{text}{styles['end']}"
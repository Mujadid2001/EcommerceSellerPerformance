"""
Management command to seed sample data for testing

Usage:
    python manage.py seed_performance_data
    python manage.py seed_performance_data --sellers=10 --orders=50
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import random

from apps.performance.models import Seller, Order, CustomerFeedback
from apps.performance.services import StatusAssignmentService

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed sample performance data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--sellers',
            type=int,
            default=5,
            help='Number of sellers to create',
        )
        parser.add_argument(
            '--orders',
            type=int,
            default=20,
            help='Number of orders per seller',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )
    
    def handle(self, *args, **options):
        num_sellers = options['sellers']
        orders_per_seller = options['orders']
        clear_data = options['clear']
        
        if clear_data:
            self.stdout.write('Clearing existing data...')
            CustomerFeedback.objects.all().delete()
            Order.objects.all().delete()
            Seller.objects.all().delete()
            User.objects.filter(email__startswith='seller').delete()
        
        self.stdout.write(f'Creating {num_sellers} sellers...')
        
        business_names = [
            'TechGear Solutions', 'Fashion Forward', 'Home Essentials',
            'Sports Pro Shop', 'Beauty Bliss', 'Book Haven',
            'Pet Paradise', 'Kitchen Masters', 'Gadget Galaxy',
            'Outdoor Adventures', 'Music Corner', 'Auto Parts Plus'
        ]
        
        sellers = []
        for i in range(num_sellers):
            # Create user
            user = User.objects.create_user(
                email=f'seller{i+1}@marketplace.com',
                password='testpass123',
                first_name=f'Seller{i+1}',
                last_name='Account'
            )
            
            # Create seller
            seller = Seller.objects.create(
                user=user,
                business_name=business_names[i % len(business_names)] + f' #{i+1}',
                business_registration=f'REG{i+1:06d}',
                description=f'Quality products from {business_names[i % len(business_names)]}'
            )
            sellers.append(seller)
            
            self.stdout.write(f'  Created: {seller.business_name}')
        
        self.stdout.write(f'\nCreating orders and feedback...')
        
        order_statuses = [
            (Order.Status.DELIVERED, 70),  # 70% delivered
            (Order.Status.RETURNED, 10),   # 10% returned
            (Order.Status.PROCESSING, 10), # 10% processing
            (Order.Status.SHIPPED, 10),    # 10% shipped
        ]
        
        for seller in sellers:
            for j in range(orders_per_seller):
                # Weighted random status
                status = random.choices(
                    [s[0] for s in order_statuses],
                    weights=[s[1] for s in order_statuses]
                )[0]
                
                # Random order details
                days_ago = random.randint(1, 90)
                order_date = timezone.now() - timedelta(days=days_ago)
                order_amount = Decimal(str(random.uniform(20, 500))).quantize(Decimal('0.01'))
                
                # Create order
                order = Order.objects.create(
                    seller=seller,
                    order_number=f'ORD{seller.id}{j+1:04d}',
                    customer_email=f'customer{random.randint(1, 100)}@example.com',
                    order_amount=order_amount,
                    status=status,
                    order_date=order_date
                )
                
                # Add delivery info for delivered/returned orders
                if status in [Order.Status.DELIVERED, Order.Status.RETURNED]:
                    delivery_days = random.randint(1, 14)
                    order.shipped_date = order_date + timedelta(days=1)
                    order.delivered_date = order_date + timedelta(days=delivery_days)
                    order.delivery_days = delivery_days
                    
                    if status == Order.Status.RETURNED:
                        order.is_returned = True
                        order.return_date = order.delivered_date + timedelta(days=random.randint(1, 7))
                        order.return_reason = random.choice([
                            'Wrong item received',
                            'Product damaged',
                            'Not as described',
                            'Changed mind'
                        ])
                    
                    order.save()
                    
                    # Add feedback for some delivered (non-returned) orders
                    if status == Order.Status.DELIVERED and random.random() > 0.3:
                        # Higher ratings more likely
                        rating = random.choices(
                            [1, 2, 3, 4, 5],
                            weights=[5, 10, 15, 30, 40]
                        )[0]
                        
                        CustomerFeedback.objects.create(
                            seller=seller,
                            order=order,
                            customer_email=order.customer_email,
                            rating=rating,
                            comment=f'{"Great" if rating >= 4 else "Okay" if rating == 3 else "Poor"} experience'
                        )
        
        self.stdout.write(self.style.SUCCESS(f'\nCreated {Order.objects.count()} orders'))
        self.stdout.write(self.style.SUCCESS(f'Created {CustomerFeedback.objects.count()} feedbacks'))
        
        # Evaluate all sellers
        self.stdout.write(f'\nEvaluating seller performance...')
        for seller in sellers:
            StatusAssignmentService.evaluate_and_assign(seller)
            seller.refresh_from_db()
            self.stdout.write(
                f'  {seller.business_name}: '
                f'Score={seller.performance_score:.2f}, '
                f'Status={seller.get_status_display()}'
            )
        
        self.stdout.write(self.style.SUCCESS('\nData seeding complete!'))
        self.stdout.write('You can now access the admin panel to view the data.')

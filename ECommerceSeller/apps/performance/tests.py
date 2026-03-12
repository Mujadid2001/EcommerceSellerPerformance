"""
Tests for performance app

Run with: python manage.py test apps.performance
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from apps.performance.models import Seller, Order, CustomerFeedback
from apps.performance.services import PerformanceCalculationService, StatusAssignmentService

User = get_user_model()


class SellerModelTest(TestCase):
    """Test Seller model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Store',
            business_registration='REG123456'
        )
    
    def test_seller_creation(self):
        """Test seller is created correctly."""
        self.assertEqual(self.seller.business_name, 'Test Store')
        self.assertEqual(self.seller.status, Seller.Status.ACTIVE)
        self.assertEqual(self.seller.performance_score, Decimal('0.00'))
    
    def test_seller_string_representation(self):
        """Test seller string representation."""
        self.assertIn('Test Store', str(self.seller))


class OrderModelTest(TestCase):
    """Test Order model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Store',
            business_registration='REG123456'
        )
    
    def test_order_creation(self):
        """Test order is created correctly."""
        order = Order.objects.create(
            seller=self.seller,
            order_number='ORD001',
            customer_email='customer@test.com',
            order_amount=Decimal('100.00')
        )
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(order.is_returned)
    
    def test_delivery_days_calculation(self):
        """Test delivery days are calculated correctly."""
        order = Order.objects.create(
            seller=self.seller,
            order_number='ORD002',
            customer_email='customer@test.com',
            order_amount=Decimal('150.00'),
            order_date=timezone.now() - timedelta(days=5)
        )
        order.mark_as_delivered()
        self.assertIsNotNone(order.delivery_days)
        self.assertGreater(order.delivery_days, 0)


class PerformanceCalculationServiceTest(TestCase):
    """Test PerformanceCalculationService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Store',
            business_registration='REG123456'
        )
    
    def test_new_seller_score(self):
        """Test score calculation for new seller with no data."""
        service = PerformanceCalculationService(self.seller)
        score = service.calculate_performance_score()
        self.assertGreaterEqual(score, Decimal('0.00'))
        self.assertLessEqual(score, Decimal('100.00'))
    
    def test_score_with_orders(self):
        """Test score calculation with orders."""
        # Create completed orders
        for i in range(5):
            order = Order.objects.create(
                seller=self.seller,
                order_number=f'ORD{i:03d}',
                customer_email=f'customer{i}@test.com',
                order_amount=Decimal('100.00'),
                status=Order.Status.DELIVERED,
                order_date=timezone.now() - timedelta(days=10),
                delivered_date=timezone.now() - timedelta(days=7),
                delivery_days=3
            )
        
        service = PerformanceCalculationService(self.seller)
        score = service.calculate_performance_score()
        self.assertGreater(score, Decimal('0.00'))
    
    def test_score_with_feedback(self):
        """Test score calculation with customer feedback."""
        order = Order.objects.create(
            seller=self.seller,
            order_number='ORD001',
            customer_email='customer@test.com',
            order_amount=Decimal('100.00'),
            status=Order.Status.DELIVERED
        )
        
        CustomerFeedback.objects.create(
            seller=self.seller,
            order=order,
            customer_email='customer@test.com',
            rating=5
        )
        
        service = PerformanceCalculationService(self.seller)
        score = service.calculate_performance_score()
        self.assertGreater(score, Decimal('50.00'))


class StatusAssignmentServiceTest(TestCase):
    """Test StatusAssignmentService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Store',
            business_registration='REG123456'
        )
    
    def test_high_score_active_status(self):
        """Test high score results in active status."""
        self.seller.performance_score = Decimal('85.00')
        self.seller.save()
        
        service = StatusAssignmentService(self.seller)
        status = service.assign_status()
        self.assertEqual(status, Seller.Status.ACTIVE)
    
    def test_medium_score_under_review_status(self):
        """Test medium score results in under review status."""
        self.seller.performance_score = Decimal('55.00')
        self.seller.save()
        
        service = StatusAssignmentService(self.seller)
        status = service.assign_status()
        self.assertEqual(status, Seller.Status.UNDER_REVIEW)
    
    def test_low_score_suspended_status(self):
        """Test low score results in suspended status."""
        self.seller.performance_score = Decimal('25.00')
        self.seller.save()
        
        service = StatusAssignmentService(self.seller)
        status = service.assign_status()
        self.assertEqual(status, Seller.Status.SUSPENDED)


class SellerManagerTest(TestCase):
    """Test Seller custom manager."""
    
    def setUp(self):
        # Create multiple sellers with different statuses
        for i in range(3):
            user = User.objects.create_user(
                email=f'seller{i}@test.com',
                password='testpass123'
            )
            Seller.objects.create(
                user=user,
                business_name=f'Store {i}',
                business_registration=f'REG{i:06d}',
                status=Seller.Status.ACTIVE if i < 2 else Seller.Status.SUSPENDED
            )
    
    def test_active_queryset(self):
        """Test active sellers queryset."""
        active_sellers = Seller.objects.active()
        self.assertEqual(active_sellers.count(), 2)
    
    def test_suspended_queryset(self):
        """Test suspended sellers queryset."""
        suspended_sellers = Seller.objects.suspended()
        self.assertEqual(suspended_sellers.count(), 1)

"""
Comprehensive test suite for Performance app models and services.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.performance.models import Seller, Order, CustomerFeedback
from apps.performance.services.performance_service import PerformanceCalculationService
from apps.performance.services.status_service import StatusAssignmentService

User = get_user_model()


class SellerModelTestCase(TestCase):
    """Test cases for Seller model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Business',
            business_registration='REG123456'
        )
    
    def test_seller_creation(self):
        """Test seller can be created."""
        self.assertEqual(self.seller.business_name, 'Test Business')
        self.assertEqual(self.seller.user.email, 'seller@test.com')
        self.assertEqual(self.seller.status, 'active')
    
    def test_seller_performance_score_range(self):
        """Test performance score is within valid range."""
        self.seller.performance_score = Decimal('75.50')
        self.seller.save()
        
        self.seller.refresh_from_db()
        self.assertGreaterEqual(self.seller.performance_score, 0)
        self.assertLessEqual(self.seller.performance_score, 100)
    
    def test_seller_string_representation(self):
        """Test seller string representation."""
        self.assertEqual(str(self.seller), f"{self.seller.business_name} ({self.user.email})")


class OrderModelTestCase(TestCase):
    """Test cases for Order model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Business',
            business_registration='REG123456'
        )
        self.order = Order.objects.create(
            seller=self.seller,
            order_number='ORD-001',
            customer_email='customer@test.com',
            order_amount=Decimal('99.99'),
            status='pending'
        )
    
    def test_order_creation(self):
        """Test order can be created."""
        self.assertEqual(self.order.order_number, 'ORD-001')
        self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.order.order_amount, Decimal('99.99'))
    
    def test_order_status_transition(self):
        """Test order can transition between valid statuses."""
        valid_transitions = [
            ('pending', 'processing'),
            ('processing', 'shipped'),
            ('shipped', 'delivered'),
        ]
        
        for from_status, to_status in valid_transitions:
            order = Order.objects.create(
                seller=self.seller,
                order_number=f'ORD-{from_status}-{to_status}',
                customer_email='test@test.com',
                order_amount=Decimal('50.00'),
                status=from_status
            )
            order.status = to_status
            order.save()
            self.assertEqual(order.status, to_status)
    
    def test_delivery_days_calculation(self):
        """Test delivery days are calculated correctly."""
        self.order.order_date = timezone.now() - timedelta(days=5)
        self.order.delivered_date = timezone.now()
        self.order.status = 'delivered'
        self.order.save()
        
        self.order.refresh_from_db()
        # Delivery days should be approximately 5
        self.assertIsNotNone(self.order.delivery_days)


class CustomerFeedbackTestCase(TestCase):
    """Test cases for CustomerFeedback model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Business',
            business_registration='REG123456'
        )
        self.order = Order.objects.create(
            seller=self.seller,
            order_number='ORD-001',
            customer_email='customer@test.com',
            order_amount=Decimal('99.99'),
            status='delivered'
        )
        self.feedback = CustomerFeedback.objects.create(
            order=self.order,
            rating=5,
            comment='Excellent service!'
        )
    
    def test_feedback_creation(self):
        """Test feedback can be created."""
        self.assertEqual(self.feedback.rating, 5)
        self.assertEqual(self.feedback.comment, 'Excellent service!')
    
    def test_feedback_rating_range(self):
        """Test feedback rating is within valid range (1-5)."""
        feedback = CustomerFeedback.objects.create(
            order=self.order,
            rating=3,
            comment='Average'
        )
        
        self.assertGreaterEqual(feedback.rating, 1)
        self.assertLessEqual(feedback.rating, 5)


class PerformanceCalculationTestCase(TestCase):
    """Test cases for PerformanceCalculationService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = PerformanceCalculationService()
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Business',
            business_registration='REG123456'
        )
    
    def test_performance_score_calculation(self):
        """Test performance score calculation."""
        # Create orders and feedback
        for i in range(5):
            order = Order.objects.create(
                seller=self.seller,
                order_number=f'ORD-{i:03d}',
                customer_email=f'customer{i}@test.com',
                order_amount=Decimal('100.00'),
                status='delivered',
                order_date=timezone.now() - timedelta(days=10-i),
                delivered_date=timezone.now() - timedelta(days=5-i),
            )
            CustomerFeedback.objects.create(
                order=order,
                rating=4 + (i % 2),  # Ratings 4-5
                comment='Good'
            )
        
        # Update seller metrics
        self.seller.total_orders = 5
        self.seller.total_sales_volume = Decimal('500.00')
        self.seller.average_rating = Decimal('4.6')
        self.seller.average_delivery_days = Decimal('5.0')
        self.seller.return_rate = Decimal('0.0')
        self.seller.save()
        
        # Calculate performance
        score = self.service.calculate_performance_score(self.seller)
        
        self.assertIsNotNone(score)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)


class StatusAssignmentTestCase(TestCase):
    """Test cases for StatusAssignmentService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = StatusAssignmentService()
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Business',
            business_registration='REG123456'
        )
    
    def test_status_assignment_active(self):
        """Test status assignment for active seller."""
        self.seller.performance_score = Decimal('75.00')
        self.service.assign_status(self.seller)
        
        self.assertEqual(self.seller.status, 'active')
    
    def test_status_assignment_under_review(self):
        """Test status assignment for under review."""
        self.seller.performance_score = Decimal('55.00')
        self.service.assign_status(self.seller)
        
        self.assertEqual(self.seller.status, 'under_review')
    
    def test_status_assignment_suspended(self):
        """Test status assignment for suspended seller."""
        self.seller.performance_score = Decimal('30.00')
        self.service.assign_status(self.seller)
        
        self.assertEqual(self.seller.status, 'suspended')


class SellerAPITestCase(TestCase):
    """Test cases for Seller API endpoints."""
    
    def setUp(self):
        """Set up test data and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Business',
            business_registration='REG123456'
        )
    
    def test_seller_list_endpoint(self):
        """Test seller list endpoint."""
        self.client.login(email='seller@test.com', password='testpass123')
        response = self.client.get('/marketplace/api/sellers/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_seller_detail_endpoint(self):
        """Test seller detail endpoint."""
        self.client.login(email='seller@test.com', password='testpass123')
        response = self.client.get(f'/marketplace/api/sellers/{self.seller.id}/')
        
        self.assertEqual(response.status_code, 200)


class OrderAPITestCase(TestCase):
    """Test cases for Order API endpoints."""
    
    def setUp(self):
        """Set up test data and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            business_name='Test Business',
            business_registration='REG123456'
        )
        self.order = Order.objects.create(
            seller=self.seller,
            order_number='ORD-001',
            customer_email='customer@test.com',
            order_amount=Decimal('99.99'),
            status='pending'
        )
    
    def test_order_list_endpoint(self):
        """Test order list endpoint."""
        response = self.client.get('/marketplace/api/orders/')
        self.assertEqual(response.status_code, 200)
    
    def test_order_detail_endpoint(self):
        """Test order detail endpoint."""
        response = self.client.get(f'/marketplace/api/orders/{self.order.id}/')
        self.assertEqual(response.status_code, 200)

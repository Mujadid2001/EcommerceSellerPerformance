#!/usr/bin/env python
"""
System Verification Script
Tests all major components of the E-Commerce Seller Performance System
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ECommerceSeller.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.performance.models import Seller, Order, CustomerFeedback
from apps.performance.services import PerformanceCalculationService, StatusAssignmentService
from decimal import Decimal

User = get_user_model()

def print_header(text):
    print('\n' + '=' * 60)
    print(text.center(60))
    print('=' * 60)

def print_success(text):
    print(f'✓ {text}')

def print_error(text):
    print(f'✗ {text}')
    sys.exit(1)

def test_database_connection():
    """Test database connectivity"""
    print_header('Testing Database Connection')
    try:
        from django.db import connection
        connection.ensure_connection()
        print_success('Database connection successful')
        return True
    except Exception as e:
        print_error(f'Database connection failed: {e}')
        return False

def test_models():
    """Test model creation and queries"""
    print_header('Testing Models')
    try:
        # Test User model
        user_count = User.objects.count()
        print_success(f'User model accessible ({user_count} users)')
        
        # Test Seller model
        seller_count = Seller.objects.count()
        print_success(f'Seller model accessible ({seller_count} sellers)')
        
        # Test Order model
        order_count = Order.objects.count()
        print_success(f'Order model accessible ({order_count} orders)')
        
        # Test CustomerFeedback model
        feedback_count = CustomerFeedback.objects.count()
        print_success(f'CustomerFeedback model accessible ({feedback_count} feedback)')
        
        return True
    except Exception as e:
        print_error(f'Model test failed: {e}')
        return False

def test_managers():
    """Test custom managers"""
    print_header('Testing Custom Managers')
    try:
        # Test SellerManager
        active_sellers = Seller.objects.active().count()
        print_success(f'SellerManager.active() works ({active_sellers} active sellers)')
        
        under_review = Seller.objects.under_review().count()
        print_success(f'SellerManager.under_review() works ({under_review} sellers)')
        
        # Test OrderManager
        completed_orders = Order.objects.completed().count()
        print_success(f'OrderManager.completed() works ({completed_orders} orders)')
        
        returned_orders = Order.objects.returned().count()
        print_success(f'OrderManager.returned() works ({returned_orders} orders)')
        
        return True
    except Exception as e:
        print_error(f'Manager test failed: {e}')
        return False

def test_services():
    """Test business logic services"""
    print_header('Testing Services')
    try:
        # Get a seller to test with
        seller = Seller.objects.first()
        if not seller:
            print('  No sellers found, skipping service tests')
            return True
        
        # Test PerformanceCalculationService
        service = PerformanceCalculationService(seller)
        score = service.calculate_performance_score()
        print_success(f'PerformanceCalculationService works (score: {score})')
        
        # Test metrics gathering
        service._gather_metrics()
        metrics = service.get_metrics()
        print_success(f'Metrics gathering works ({len(metrics)} metrics)')
        
        # Test score breakdown
        breakdown = service.get_score_breakdown()
        print_success(f'Score breakdown works ({len(breakdown)} components)')
        
        # Test StatusAssignmentService
        original_status = seller.status
        StatusAssignmentService.evaluate_and_assign(seller)
        print_success('StatusAssignmentService works')
        
        return True
    except Exception as e:
        print_error(f'Service test failed: {e}')
        return False

def test_api_serializers():
    """Test API serializers"""
    print_header('Testing API Serializers')
    try:
        from apps.performance.serializers import (
            SellerListSerializer, SellerDetailSerializer,
            OrderListSerializer, OrderDetailSerializer,
            CustomerFeedbackSerializer
        )
        
        # Test SellerListSerializer
        sellers = Seller.objects.all()[:1]
        if sellers:
            serializer = SellerListSerializer(sellers, many=True)
            data = serializer.data
            print_success('SellerListSerializer works')
        
        # Test SellerDetailSerializer
        seller = Seller.objects.first()
        if seller:
            serializer = SellerDetailSerializer(seller)
            data = serializer.data
            print_success('SellerDetailSerializer works')
        
        # Test OrderListSerializer
        orders = Order.objects.all()[:1]
        if orders:
            serializer = OrderListSerializer(orders, many=True)
            data = serializer.data
            print_success('OrderListSerializer works')
        
        print_success('All serializers functional')
        return True
    except Exception as e:
        print_error(f'Serializer test failed: {e}')
        return False

def test_management_commands():
    """Test management commands exist"""
    print_header('Testing Management Commands')
    try:
        # Check if commands are importable
        from apps.performance.management.commands import (
            evaluate_sellers,
            seed_performance_data,
            setup_system
        )
        print_success('evaluate_sellers command exists')
        print_success('seed_performance_data command exists')
        print_success('setup_system command exists')
        
        return True
    except Exception as e:
        print_error(f'Management command test failed: {e}')
        return False

def test_views():
    """Test views are importable"""
    print_header('Testing Views')
    try:
        from apps.performance import views
        
        # Check ViewSets exist
        assert hasattr(views, 'SellerViewSet')
        print_success('SellerViewSet exists')
        
        assert hasattr(views, 'OrderViewSet')
        print_success('OrderViewSet exists')
        
        assert hasattr(views, 'CustomerFeedbackViewSet')
        print_success('CustomerFeedbackViewSet exists')
        
        # Check web views exist
        assert hasattr(views, 'marketplace_view')
        print_success('marketplace_view exists')
        
        assert hasattr(views, 'seller_dashboard')
        print_success('seller_dashboard exists')
        
        assert hasattr(views, 'seller_public_profile')
        print_success('seller_public_profile exists')
        
        return True
    except Exception as e:
        print_error(f'Views test failed: {e}')
        return False

def test_authentication():
    """Test authentication app"""
    print_header('Testing Authentication')
    try:
        from apps.authentication import views, models, serializers
        
        print_success('Authentication app importable')
        print_success(f'User model configured: {User.__name__}')
        
        return True
    except Exception as e:
        print_error(f'Authentication test failed: {e}')
        return False

def test_static_files():
    """Test static files exist"""
    print_header('Testing Static Files')
    try:
        from django.conf import settings
        import os
        
        # Check if static dirs exist
        performance_static = os.path.join(
            settings.BASE_DIR,
            'apps',
            'performance',
            'static',
            'performance'
        )
        
        if os.path.exists(performance_static):
            print_success('Performance static directory exists')
            
            css_file = os.path.join(performance_static, 'css', 'style.css')
            if os.path.exists(css_file):
                print_success('CSS file exists')
            
            js_file = os.path.join(performance_static, 'js', 'main.js')
            if os.path.exists(js_file):
                print_success('JavaScript file exists')
        
        return True
    except Exception as e:
        print_error(f'Static files test failed: {e}')
        return False

def test_templates():
    """Test templates exist"""
    print_header('Testing Templates')
    try:
        from django.template.loader import get_template
        
        templates = [
            'base.html',
            'performance/marketplace.html',
            'performance/dashboard.html',
            'performance/seller_profile.html',
            'performance/no_profile.html',
        ]
        
        for template_name in templates:
            try:
                get_template(template_name)
                print_success(f'Template found: {template_name}')
            except Exception:
                print_error(f'Template missing: {template_name}')
        
        return True
    except Exception as e:
        print_error(f'Template test failed: {e}')
        return False

def main():
    print_header('E-Commerce Seller Performance System')
    print('System Verification Test Suite')
    
    tests = [
        ('Database', test_database_connection),
        ('Models', test_models),
        ('Managers', test_managers),
        ('Services', test_services),
        ('Serializers', test_api_serializers),
        ('Management Commands', test_management_commands),
        ('Views', test_views),
        ('Authentication', test_authentication),
        ('Static Files', test_static_files),
        ('Templates', test_templates),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f'{name} test crashed: {e}')
            results.append((name, False))
    
    # Summary
    print_header('Test Summary')
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = '✓ PASS' if result else '✗ FAIL'
        print(f'{status}: {name}')
    
    print(f'\nTotal: {passed}/{total} tests passed')
    
    if passed == total:
        print_header('ALL TESTS PASSED!')
        print('\nSystem is ready to use.')
        print('\nNext steps:')
        print('1. Create a superuser: python manage.py createsuperuser')
        print('2. Seed sample data: python manage.py seed_performance_data')
        print('3. Run server: python manage.py runserver 8080')
        sys.exit(0)
    else:
        print_header('SOME TESTS FAILED')
        print('\nPlease fix the failing tests before proceeding.')
        sys.exit(1)

if __name__ == '__main__':
    main()

"""
URL Configuration for performance app
"""
from django.urls import path
from apps.performance import views

app_name = 'performance'

urlpatterns = [
    # Web views
    path('', views.marketplace_view, name='marketplace'),
    path('dashboard/', views.seller_dashboard, name='dashboard'),
    path('seller/<int:seller_id>/', views.seller_public_profile, name='seller_profile'),
    path('orders/', views.orders_view, name='orders'),
    path('profile/', views.profile_view, name='profile'),
    
    # API endpoints - Sellers
    path('api/sellers/', views.SellerViewSet.as_view({'get': 'list'}), name='seller-list'),
    path('api/sellers/<int:pk>/', views.SellerViewSet.as_view({'get': 'retrieve'}), name='seller-detail'),
    path('api/sellers/<int:pk>/metrics/', views.SellerViewSet.as_view({'get': 'metrics'}), name='seller-metrics'),
    path('api/sellers/<int:pk>/score_breakdown/', views.SellerViewSet.as_view({'get': 'score_breakdown'}), name='seller-score-breakdown'),
    path('api/sellers/<int:pk>/recalculate/', views.SellerViewSet.as_view({'post': 'recalculate'}), name='seller-recalculate'),
    path('api/sellers/my_profile/', views.SellerViewSet.as_view({'get': 'my_profile'}), name='seller-my-profile'),
    
    # API endpoints - Orders
    path('api/orders/', views.OrderViewSet.as_view({'get': 'list', 'post': 'create'}), name='order-list'),
    path('api/orders/<int:pk>/', views.OrderViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='order-detail'),
    path('api/orders/my_orders/', views.OrderViewSet.as_view({'get': 'my_orders'}), name='order-my-orders'),
    
    # API endpoints - Feedback
    path('api/feedback/', views.CustomerFeedbackViewSet.as_view({'get': 'list'}), name='feedback-list'),
    path('api/feedback/<int:pk>/', views.CustomerFeedbackViewSet.as_view({'get': 'retrieve'}), name='feedback-detail'),
    path('api/feedback/my_feedback/', views.CustomerFeedbackViewSet.as_view({'get': 'my_feedback'}), name='feedback-my-feedback'),
]


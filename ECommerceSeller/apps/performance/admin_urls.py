"""
URL Configuration for Admin Interface
"""
from django.urls import path
from . import admin_views

app_name = 'admin_perf'

urlpatterns = [
    # Main admin dashboard
    path('', admin_views.admin_dashboard, name='dashboard'),
    
    # Seller management
    path('sellers/', admin_views.seller_management, name='seller_management'),
    path('sellers/<int:seller_id>/', admin_views.seller_detail_admin, name='seller_detail'),
    
    # Data import/export
    path('import/', admin_views.data_import_view, name='data_import'),
    path('import/process/', admin_views.handle_data_import, name='handle_import'),
    path('export/', admin_views.data_export_view, name='data_export'),
    path('export/generate/', admin_views.generate_export, name='generate_export'),
    
    # AI insights
    path('ai-insights/', admin_views.ai_insights_dashboard, name='ai_insights'),
    path('sellers/<int:seller_id>/ai-analysis/', admin_views.trigger_ai_analysis, name='trigger_ai_analysis'),
    
    # System monitoring
    path('health/', admin_views.system_health_check, name='system_health'),
]
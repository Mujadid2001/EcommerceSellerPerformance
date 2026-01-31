"""
Performance app configuration
"""
from django.apps import AppConfig


class PerformanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.performance'
    verbose_name = 'Seller Performance'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.performance.signals

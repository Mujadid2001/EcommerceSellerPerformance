# This allows us to access our Celery app as a project level instance of Celery
from .celery import app as celery_app

__all__ = ('celery_app',)

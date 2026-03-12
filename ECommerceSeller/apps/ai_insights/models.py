"""
AI Insights models for intelligent performance analysis.
Implements AI-FR-01: AI-Powered Performance Insights & Recommendations.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class PerformanceInsight(models.Model):
    """
    AI-generated insights about seller performance trends and patterns.
    """
    
    class InsightType(models.TextChoices):
        """Types of AI insights."""
        TREND_ANALYSIS = 'trend_analysis', 'Trend Analysis'
        PERFORMANCE_ALERT = 'performance_alert', 'Performance Alert'
        RECOMMENDATION = 'recommendation', 'Recommendation'
        PREDICTION = 'prediction', 'Prediction'
        RANKING_CHANGE = 'ranking_change', 'Ranking Change'
        BENCHMARK_COMPARISON = 'benchmark_comparison', 'Benchmark Comparison'
    
    class Severity(models.TextChoices):
        """Insight severity levels."""
        INFO = 'info', 'Information'
        LOW = 'low', 'Low Priority'
        MEDIUM = 'medium', 'Medium Priority'
        HIGH = 'high', 'High Priority'
        CRITICAL = 'critical', 'Critical'
    
    class Status(models.TextChoices):
        """Insight status."""
        ACTIVE = 'active', 'Active'
        ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed'
    
    # Identification
    insight_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    
    # Target seller
    seller = models.ForeignKey(
        'performance.Seller',
        on_delete=models.CASCADE,
        related_name='ai_insights'
    )
    
    # Insight details
    insight_type = models.CharField(
        max_length=30,
        choices=InsightType.choices,
        db_index=True
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.INFO,
        db_index=True
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    
    # Content
    title = models.CharField(max_length=255)
    description = models.TextField()
    recommendation = models.TextField(blank=True)
    
    # AI analysis data
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="AI confidence level (0-100%)"
    )
    
    # Metrics and data
    analysis_data = models.JSONField(
        default=dict,
        help_text="Raw analysis data and metrics"
    )
    
    # Predictions (if applicable)
    predicted_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Predicted metric value"
    )
    prediction_timeframe_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Prediction timeframe in days"
    )
    
    # Management
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_insights'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this insight becomes irrelevant"
    )
    
    class Meta:
        verbose_name = "Performance Insight"
        verbose_name_plural = "Performance Insights"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['insight_type', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.seller.business_name}"
    
    def acknowledge(self, user):
        """Mark insight as acknowledged by user."""
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.status = self.Status.ACKNOWLEDGED
        self.save()
    
    def is_expired(self):
        """Check if insight has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class AIModel(models.Model):
    """
    AI model metadata and performance tracking.
    """
    
    class ModelType(models.TextChoices):
        """Types of AI models."""
        PERFORMANCE_PREDICTOR = 'performance_predictor', 'Performance Predictor'
        TREND_ANALYZER = 'trend_analyzer', 'Trend Analyzer'
        ANOMALY_DETECTOR = 'anomaly_detector', 'Anomaly Detector'
        RECOMMENDATION_ENGINE = 'recommendation_engine', 'Recommendation Engine'
    
    class Status(models.TextChoices):
        """Model status."""
        TRAINING = 'training', 'Training'
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        DEPRECATED = 'deprecated', 'Deprecated'
    
    # Model identification
    name = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=20)
    model_type = models.CharField(
        max_length=30,
        choices=ModelType.choices
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.TRAINING
    )
    
    # Model configuration
    config = models.JSONField(
        default=dict,
        help_text="Model configuration parameters"
    )
    
    # Performance metrics
    accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    precision = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    recall = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    
    # Usage statistics
    total_predictions = models.PositiveIntegerField(default=0)
    last_trained_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Model"
        verbose_name_plural = "AI Models"
        ordering = ['-created_at']
        unique_together = ['name', 'version']
    
    def __str__(self):
        return f"{self.name} v{self.version}"


class PredictiveAlert(models.Model):
    """
    Predictive alerts for proactive seller management.
    """
    
    class AlertType(models.TextChoices):
        """Types of predictive alerts."""
        PERFORMANCE_DECLINE = 'performance_decline', 'Performance Decline'
        RETURN_RATE_SPIKE = 'return_rate_spike', 'Return Rate Spike'
        DELIVERY_DELAY_RISK = 'delivery_delay_risk', 'Delivery Delay Risk'
        RATING_DROP_RISK = 'rating_drop_risk', 'Rating Drop Risk'
        SALES_DECLINE = 'sales_decline', 'Sales Decline'
        THRESHOLD_BREACH = 'threshold_breach', 'Threshold Breach'
    
    class Priority(models.TextChoices):
        """Alert priority levels."""
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    # Target seller
    seller = models.ForeignKey(
        'performance.Seller',
        on_delete=models.CASCADE,
        related_name='predictive_alerts'
    )
    
    # Alert details
    alert_type = models.CharField(
        max_length=30,
        choices=AlertType.choices,
        db_index=True
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True
    )
    
    # Content
    title = models.CharField(max_length=255)
    message = models.TextField()
    suggested_actions = models.TextField(blank=True)
    
    # Prediction details
    predicted_metric = models.CharField(max_length=100)
    current_value = models.DecimalField(max_digits=10, decimal_places=2)
    predicted_value = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    
    # Timeline
    prediction_date = models.DateTimeField(
        help_text="When the predicted event is expected to occur"
    )
    
    # Management
    is_active = models.BooleanField(default=True, db_index=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Predictive Alert"
        verbose_name_plural = "Predictive Alerts"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['alert_type', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.seller.business_name}"
    
    def acknowledge(self, user):
        """Mark alert as acknowledged."""
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()


class RankingChange(models.Model):
    """
    Track and analyze seller ranking changes with AI insights.
    """
    
    seller = models.ForeignKey(
        'performance.Seller',
        on_delete=models.CASCADE,
        related_name='ranking_changes'
    )
    
    # Ranking data
    previous_rank = models.PositiveIntegerField()
    new_rank = models.PositiveIntegerField()
    rank_change = models.IntegerField()  # Positive = moved up, Negative = moved down
    
    # Performance scores
    previous_score = models.DecimalField(max_digits=5, decimal_places=2)
    new_score = models.DecimalField(max_digits=5, decimal_places=2)
    score_change = models.DecimalField(max_digits=5, decimal_places=2)
    
    # AI analysis  
    change_factors = models.JSONField(
        default=dict,
        help_text="AI-identified factors contributing to ranking change"
    )
    ai_summary = models.TextField(
        blank=True,
        help_text="AI-generated summary of ranking change"
    )
    
    # Timestamps
    change_date = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Ranking Change"
        verbose_name_plural = "Ranking Changes"
        ordering = ['-change_date']
        indexes = [
            models.Index(fields=['seller', '-change_date']),
        ]
    
    def __str__(self):
        direction = "↑" if self.rank_change > 0 else "↓"
        return f"{self.seller.business_name} {direction} {abs(self.rank_change)} positions"
    
    def get_change_direction(self):
        """Get human-readable change direction."""
        if self.rank_change > 0:
            return f"Moved up {self.rank_change} positions"
        elif self.rank_change < 0:
            return f"Moved down {abs(self.rank_change)} positions"
        else:
            return "No change in position"
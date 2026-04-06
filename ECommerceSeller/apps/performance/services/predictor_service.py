"""
Performance Predictor Service for what-if scenario analysis.
Allows sellers to simulate performance changes and see predicted outcomes.
"""
from decimal import Decimal
from typing import Dict, Any
from django.conf import settings


class PerformancePredictorService:
    """
    Service for predicting performance score based on adjusted metrics.
    Helps sellers understand which actions have the biggest impact.
    """
    
    def __init__(self):
        """Initialize with configuration from settings."""
        self.weights = getattr(settings, 'PERFORMANCE_SCORE_WEIGHTS', {
            'sales': 30,
            'delivery': 25,
            'rating': 35,
            'returns': 10,
        })
        
        # Sales thresholds
        self.sales_excellent = getattr(settings, 'PERFORMANCE_SALES_EXCELLENT', 100000)
        self.sales_good = getattr(settings, 'PERFORMANCE_SALES_GOOD', 50000)
        self.sales_low = getattr(settings, 'PERFORMANCE_SALES_LOW', 10000)
        
        # Delivery thresholds (days)
        self.delivery_excellent = getattr(settings, 'PERFORMANCE_DELIVERY_EXCELLENT', 2)
        self.delivery_good = getattr(settings, 'PERFORMANCE_DELIVERY_GOOD', 5)
        self.delivery_mid = getattr(settings, 'PERFORMANCE_DELIVERY_MID', 10)
        self.delivery_slow = getattr(settings, 'PERFORMANCE_DELIVERY_SLOW', 14)
        
        # Rating thresholds
        self.rating_excellent = 4.5
        self.rating_good = 4.0
        self.rating_mid = 3.5
        
        # Return rate thresholds
        self.return_excellent = 2.0
        self.return_good = 5.0
        self.return_mid = 10.0
        self.return_max = 20.0
    
    def calculate_predicted_score(self, 
                                 total_sales: float = 0,
                                 average_rating: float = 0,
                                 average_delivery_days: float = 0,
                                 return_rate: float = 0) -> Dict[str, Any]:
        """
        Calculate predicted performance score based on adjusted metrics.
        
        Args:
            total_sales: Adjusted total sales volume
            average_rating: Adjusted average rating (0-5)
            average_delivery_days: Adjusted average delivery days
            return_rate: Adjusted return rate percentage (0-100)
            
        Returns:
            Dict with predicted score breakdown and recommendations
        """
        # Calculate component scores
        sales_score = self._calculate_sales_score(total_sales)
        delivery_score = self._calculate_delivery_score(average_delivery_days)
        rating_score = self._calculate_rating_score(average_rating)
        returns_penalty = self._calculate_returns_penalty(return_rate)
        
        # Calculate weighted total
        total_score = (
            (sales_score * self.weights['sales']) +
            (delivery_score * self.weights['delivery']) +
            (rating_score * self.weights['rating']) -
            (returns_penalty * self.weights['returns'])
        ) / 100
        
        # Clamp to 0-100
        total_score = max(0, min(100, total_score))
        
        return {
            'total_score': round(total_score, 2),
            'sales_score': round(sales_score, 2),
            'delivery_score': round(delivery_score, 2),
            'rating_score': round(rating_score, 2),
            'returns_penalty': round(returns_penalty, 2),
            'sales_weight': self.weights['sales'],
            'delivery_weight': self.weights['delivery'],
            'rating_weight': self.weights['rating'],
            'returns_weight': self.weights['returns'],
            'status': self._get_status(total_score),
            'breakdown': self._get_breakdown_text(sales_score, delivery_score, rating_score, return_rate),
        }
    
    def _calculate_sales_score(self, total_sales: float) -> float:
        """Calculate sales component score (0-100)."""
        if total_sales >= self.sales_excellent:
            return 100.0
        elif total_sales >= self.sales_good:
            return 80.0 + (total_sales - self.sales_good) / (self.sales_excellent - self.sales_good) * 20
        elif total_sales >= self.sales_low:
            return 50.0 + (total_sales - self.sales_low) / (self.sales_good - self.sales_low) * 30
        else:
            return min(50.0, (total_sales / self.sales_low) * 50)
    
    def _calculate_delivery_score(self, days: float) -> float:
        """Calculate delivery component score (0-100)."""
        if days <= self.delivery_excellent:
            return 100.0
        elif days <= self.delivery_good:
            return 80.0 + (self.delivery_good - days) / (self.delivery_good - self.delivery_excellent) * 20
        elif days <= self.delivery_mid:
            return 50.0 + (self.delivery_mid - days) / (self.delivery_mid - self.delivery_good) * 30
        elif days <= self.delivery_slow:
            return 20.0 + (self.delivery_slow - days) / (self.delivery_slow - self.delivery_mid) * 30
        else:
            return max(0, 20.0 - ((days - self.delivery_slow) / self.delivery_slow * 20))
    
    def _calculate_rating_score(self, rating: float) -> float:
        """Calculate rating component score (0-100)."""
        if rating >= self.rating_excellent:
            return 100.0
        elif rating >= self.rating_good:
            return 80.0 + (rating - self.rating_good) / (self.rating_excellent - self.rating_good) * 20
        elif rating >= self.rating_mid:
            return 50.0 + (rating - self.rating_mid) / (self.rating_good - self.rating_mid) * 30
        else:
            return (rating / self.rating_mid) * 50
    
    def _calculate_returns_penalty(self, return_rate: float) -> float:
        """Calculate returns penalty (penalty points, 0-100)."""
        if return_rate <= self.return_excellent:
            return 0.0
        elif return_rate <= self.return_good:
            return (return_rate - self.return_excellent) / (self.return_good - self.return_excellent) * 25
        elif return_rate <= self.return_mid:
            return 25.0 + (return_rate - self.return_good) / (self.return_mid - self.return_good) * 40
        elif return_rate <= self.return_max:
            return 65.0 + (return_rate - self.return_mid) / (self.return_max - self.return_mid) * 30
        else:
            return 95.0
    
    def _get_status(self, score: float) -> str:
        """Get status badge based on score."""
        if score >= 70:
            return "Excellent"
        elif score >= 50:
            return "Good"
        else:
            return "Needs Improvement"
    
    def _get_breakdown_text(self, sales: float, delivery: float, rating: float, returns: float) -> str:
        """Generate human-readable breakdown of scores."""
        strengths = []
        weaknesses = []
        
        if sales >= 80:
            strengths.append("Strong sales performance")
        elif sales < 50:
            weaknesses.append("Low sales volume")
        
        if delivery >= 80:
            strengths.append("Fast delivery")
        elif delivery < 50:
            weaknesses.append("Slow delivery times")
        
        if rating >= 80:
            strengths.append("Excellent ratings")
        elif rating < 50:
            weaknesses.append("Low customer ratings")
        
        if returns <= 5:
            strengths.append("Low return rate")
        elif returns > 10:
            weaknesses.append("High return rate")
        
        result = []
        if strengths:
            result.append("Strengths: " + ", ".join(strengths))
        if weaknesses:
            result.append("Areas to improve: " + ", ".join(weaknesses))
        
        return " | ".join(result) if result else "Balanced performance"
    
    def get_improvement_suggestions(self, current_metrics: Dict, predicted_metrics: Dict) -> list:
        """
        Generate suggestions on which metrics to improve most.
        
        Args:
            current_metrics: Current seller metrics
            predicted_metrics: Predicted metrics from calculation
            
        Returns:
            List of suggestions with impact scores
        """
        suggestions = []
        
        # Check each component's impact
        if predicted_metrics['rating_score'] < 70:
            suggestions.append({
                'metric': 'Customer Rating',
                'current': current_metrics.get('average_rating', 0),
                'impact': self.weights['rating'],
                'suggestion': 'Improving customer ratings by 0.5 could increase your score by ' + 
                            str(round(0.5 * self.weights['rating'] / 100, 1)) + ' points',
                'priority': 'HIGH' if self.weights['rating'] >= 35 else 'MEDIUM'
            })
        
        if predicted_metrics['delivery_score'] < 70:
            suggestions.append({
                'metric': 'Delivery Speed',
                'current': current_metrics.get('average_delivery_days', 0),
                'impact': self.weights['delivery'],
                'suggestion': 'Reducing delivery time by 1 day could increase your score by ' + 
                            str(round(1 * self.weights['delivery'] / 100, 1)) + ' points',
                'priority': 'HIGH' if self.weights['delivery'] >= 25 else 'MEDIUM'
            })
        
        if predicted_metrics['sales_score'] < 70:
            suggestions.append({
                'metric': 'Sales Volume',
                'current': current_metrics.get('total_sales', 0),
                'impact': self.weights['sales'],
                'suggestion': 'Increasing sales by $10,000 could improve your score',
                'priority': 'MEDIUM'
            })
        
        if predicted_metrics['returns_penalty'] > 5:
            suggestions.append({
                'metric': 'Return Rate',
                'current': current_metrics.get('return_rate', 0),
                'impact': self.weights['returns'],
                'suggestion': 'Reducing returns by 2% could increase your score by ' + 
                            str(round(2 * self.weights['returns'] / 100, 1)) + ' points',
                'priority': 'HIGH'
            })
        
        # Sort by impact (weight)
        suggestions.sort(key=lambda x: x['impact'], reverse=True)
        return suggestions[:3]  # Top 3 suggestions

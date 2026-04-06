"""
AI Insight Service for intelligent performance analysis.
Implements AI-FR-01: AI-Powered Performance Insights & Recommendations.

This service provides:
1. Predictive alerts for performance decline
2. Automated recommendations for improvement
3. Smart ranking summaries
4. Trend analysis and anomaly detection
"""
import numpy as np
import logging
from datetime import timedelta, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Q, Max, Min
from django.conf import settings
from django.core.cache import cache

from apps.ai_insights.models import PerformanceInsight, PredictiveAlert, RankingChange, AIModel
from apps.performance.models import Seller, Order, CustomerFeedback
from apps.audit_trail.models import AuditEvent


logger = logging.getLogger(__name__)


class AIInsightService:
    """
    Core service for generating AI-powered insights and recommendations.
    Uses statistical analysis and simple ML algorithms for predictions.
    """
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'AI_PREDICTION_CACHE_TIMEOUT', 7200)  # 2 hours
        self.alert_threshold = getattr(settings, 'AI_PERFORMANCE_ALERT_THRESHOLD', 60)
        self.trend_days = getattr(settings, 'AI_TREND_ANALYSIS_DAYS', 14)  # Reduced from 30 to 14 for faster analysis
    
    def analyze_seller_performance(self, seller: Seller) -> Dict:
        """
        Comprehensive AI analysis of seller performance.
        
        Args:
            seller: Seller instance to analyze
            
        Returns:
            Dict: Analysis results with insights and recommendations
        """
        cache_key = f"ai_analysis_{seller.id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Gather historical data
            historical_data = self._gather_historical_data(seller)
            
            # Perform various analyses
            trend_analysis = self._analyze_trends(seller, historical_data)
            anomaly_detection = self._detect_anomalies(seller, historical_data)
            performance_prediction = self._predict_performance(seller, historical_data)
            recommendations = self._generate_recommendations(seller, historical_data)
            
            # Compile results
            analysis_result = {
                'seller_id': seller.id,
                'analysis_timestamp': timezone.now().isoformat(),
                'trend_analysis': trend_analysis,
                'anomaly_detection': anomaly_detection,
                'performance_prediction': performance_prediction,
                'recommendations': recommendations,
                'overall_health_score': self._calculate_health_score(seller, historical_data),
                'risk_factors': self._identify_risk_factors(seller, historical_data)
            }
            
            # Cache the result
            cache.set(cache_key, analysis_result, self.cache_timeout)
            
            # Generate insights and alerts based on analysis
            self._create_insights_from_analysis(seller, analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"AI analysis failed for seller {seller.id}: {e}")
            return {'error': str(e)}
    
    def _gather_historical_data(self, seller: Seller) -> Dict:
        """Gather historical performance data for analysis (optimized for speed)."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=self.trend_days)  # Optimized: analyze only recent data
        
        # Order data - only select needed fields for faster queries
        orders = Order.objects.filter(
            seller=seller,
            order_date__gte=start_date,
            status__in=['delivered', 'returned', 'shipped']  # Only final states
        ).only(
            'order_date', 'order_amount', 'delivery_days', 'status', 'is_returned'
        ).values(
            'order_date', 'order_amount', 'delivery_days', 'status', 'is_returned'
        )
        
        # Feedback data
        feedback = CustomerFeedback.objects.filter(
            order__seller=seller,
            created_at__gte=start_date
        ).values(
            'rating', 'created_at'
        )
        
        return {
            'orders': list(orders),
            'feedback': list(feedback),
            'date_range': {
                'start': start_date,
                'end': end_date,
                'days': self.trend_days * 2
            }
        }
    
    def _analyze_trends(self, seller: Seller, historical_data: Dict) -> Dict:
        """Analyze performance trends using statistical methods."""
        orders = historical_data['orders']
        if not orders:
            return {'error': 'Insufficient data for trend analysis'}
        
        # Group data by week for trend analysis
        weekly_metrics = {}
        
        for order in orders:
            week_start = order['order_date'] - timedelta(days=order['order_date'].weekday())
            week_key = week_start.strftime('%Y-%W')
            
            if week_key not in weekly_metrics:
                weekly_metrics[week_key] = {
                    'total_orders': 0,
                    'total_revenue': Decimal('0.00'),
                    'delivery_days': [],
                    'return_count': 0
                }
            
            weekly_metrics[week_key]['total_orders'] += 1
            weekly_metrics[week_key]['total_revenue'] += order['order_amount']
            
            if order['delivery_days']:
                weekly_metrics[week_key]['delivery_days'].append(order['delivery_days'])
            
            if order['is_returned']:
                weekly_metrics[week_key]['return_count'] += 1
        
        # Calculate trends
        weeks = sorted(weekly_metrics.keys())
        if len(weeks) < 3:
            return {'error': 'Insufficient data points for trend analysis'}
        
        # Revenue trend
        revenues = [float(weekly_metrics[week]['total_revenue']) for week in weeks]
        revenue_trend = self._calculate_trend_slope(revenues)
        
        # Order count trend
        order_counts = [weekly_metrics[week]['total_orders'] for week in weeks]
        order_trend = self._calculate_trend_slope(order_counts)
        
        # Return rate trend
        return_rates = [
            (weekly_metrics[week]['return_count'] / max(weekly_metrics[week]['total_orders'], 1)) * 100
            for week in weeks
        ]
        return_trend = self._calculate_trend_slope(return_rates)
        
        return {
            'revenue_trend': {
                'slope': revenue_trend,
                'direction': 'improving' if revenue_trend > 0 else 'declining' if revenue_trend < 0 else 'stable',
                'weekly_data': revenues
            },
            'order_trend': {
                'slope': order_trend,
                'direction': 'improving' if order_trend > 0 else 'declining' if order_trend < 0 else 'stable',
                'weekly_data': order_counts
            },
            'return_rate_trend': {
                'slope': return_trend,
                'direction': 'improving' if return_trend < 0 else 'declining' if return_trend > 0 else 'stable',
                'weekly_data': return_rates
            },
            'analysis_period_weeks': len(weeks),
            'confidence': min(len(weeks) * 10, 95)  # Simple confidence based on data points
        }
    
    def _calculate_trend_slope(self, values: List[float]) -> float:
        """Calculate linear regression slope for trend analysis."""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x = list(range(n))
        
        # Simple linear regression
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x_i * y_i for x_i, y_i in zip(x, values))
        sum_x_squared = sum(x_i ** 2 for x_i in x)
        
        if n * sum_x_squared - sum_x ** 2 == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x ** 2)
        return slope
    
    def _detect_anomalies(self, seller: Seller, historical_data: Dict) -> Dict:
        """Detect anomalies in seller performance using statistical methods."""
        orders = historical_data['orders']
        if len(orders) < 10:  # Need minimum data for anomaly detection
            return {'anomalies': [], 'note': 'Insufficient data for anomaly detection'}
        
        anomalies = []
        
        # Analyze delivery time anomalies
        delivery_times = [order['delivery_days'] for order in orders if order['delivery_days']]
        if delivery_times:
            mean_delivery = np.mean(delivery_times)
            std_delivery = np.std(delivery_times)
            
            # Flag deliveries > 2 standard deviations from mean
            for order in orders:
                if order['delivery_days'] and abs(order['delivery_days'] - mean_delivery) > 2 * std_delivery:
                    anomalies.append({
                        'type': 'delivery_anomaly',
                        'date': order['order_date'].isoformat(),
                        'value': order['delivery_days'],
                        'expected': round(mean_delivery, 2),
                        'severity': 'high' if order['delivery_days'] > mean_delivery + 2 * std_delivery else 'medium'
                    })
        
        # Analyze return rate spikes
        recent_orders = [o for o in orders if o['order_date'] >= timezone.now() - timedelta(days=7)]
        if len(recent_orders) >= 5:
            recent_return_rate = sum(1 for o in recent_orders if o['is_returned']) / len(recent_orders)
            historical_return_rate = sum(1 for o in orders if o['is_returned']) / len(orders)
            
            if recent_return_rate > historical_return_rate * 2:  # 2x increase
                anomalies.append({
                    'type': 'return_rate_spike',
                    'current_rate': round(recent_return_rate * 100, 2),
                    'historical_rate': round(historical_return_rate * 100, 2),
                    'severity': 'high',
                    'timeframe': '7 days'
                })
        
        return {
            'anomalies': anomalies,
            'total_anomalies': len(anomalies),
            'analysis_period': f"{len(orders)} orders analyzed"
        }
    
    def _predict_performance(self, seller: Seller, historical_data: Dict) -> Dict:
        """Predict future performance using trend extrapolation."""
        orders = historical_data['orders']
        if len(orders) < 5:
            return {'error': 'Insufficient data for performance prediction'}
        
        # Get recent performance metrics
        recent_orders = sorted(orders, key=lambda x: x['order_date'])[-10:]  # Last 10 orders
        
        # Calculate current averages
        current_avg_delivery = np.mean([o['delivery_days'] for o in recent_orders if o['delivery_days']])
        current_return_rate = sum(1 for o in recent_orders if o['is_returned']) / len(recent_orders)
        current_avg_revenue = np.mean([float(o['order_amount']) for o in recent_orders])
        
        # Predict next 30 days based on trends
        trends = self._analyze_trends(seller, historical_data)
        
        predictions = {
            'timeframe_days': 30,
            'predicted_performance_score': float(seller.performance_score),
            'predicted_metrics': {
                'delivery_days': current_avg_delivery,
                'return_rate': current_return_rate * 100,
                'average_revenue': current_avg_revenue
            },
            'confidence_level': 70.0  # Base confidence
        }
        
        # Adjust predictions based on trends
        if 'revenue_trend' in trends:
            revenue_change = trends['revenue_trend']['slope'] * 4  # 4 weeks projection
            predictions['predicted_metrics']['average_revenue'] += revenue_change
            
            if trends['return_rate_trend']['slope'] > 0.1:  # Increasing return rate
                predictions['predicted_performance_score'] -= 5
                predictions['risk_factors'] = ['Increasing return rate trend detected']
        
        # Generate alerts if predictions are concerning
        if predictions['predicted_performance_score'] < self.alert_threshold:
            self._create_predictive_alert(seller, 'performance_decline', predictions)
        
        return predictions
    
    def _generate_recommendations(self, seller: Seller, historical_data: Dict) -> List[Dict]:
        """Generate actionable recommendations based on performance analysis."""
        recommendations = []
        orders = historical_data['orders']
        
        if not orders:
            return recommendations
        
        # Analyze delivery performance
        delivery_times = [o['delivery_days'] for o in orders if o['delivery_days']]
        if delivery_times:
            avg_delivery = np.mean(delivery_times)
            if avg_delivery > 5:  # More than 5 days average
                recommendations.append({
                    'category': 'delivery_optimization',
                    'priority': 'high',
                    'title': 'Improve Delivery Speed',
                    'description': f'Your average delivery time is {avg_delivery:.1f} days, which is above the recommended 3-5 days.',
                    'actions': [
                        'Review your shipping process and identify bottlenecks',
                        'Consider partnering with faster delivery services',
                        'Implement better inventory management to reduce processing time'
                    ],
                    'expected_impact': 'Could improve performance score by 10-15 points'
                })
        
        # Analyze return rate
        total_orders = len(orders)
        returns = sum(1 for o in orders if o['is_returned'])
        return_rate = (returns / total_orders) * 100 if total_orders > 0 else 0
        
        if return_rate > 10:  # High return rate
            recommendations.append({
                'category': 'quality_improvement',
                'priority': 'high',
                'title': 'Reduce Return Rate',
                'description': f'Your return rate is {return_rate:.1f}%, which is above the recommended threshold of 5%.',
                'actions': [
                    'Review product descriptions for accuracy',
                    'Improve product quality control processes',
                    'Analyze return reasons to identify patterns',
                    'Enhanced product photography and descriptions'
                ],
                'expected_impact': 'Could improve performance score by 8-12 points'
            })
        
        # Revenue optimization
        recent_orders = sorted(orders, key=lambda x: x['order_date'])[-20:]
        if len(recent_orders) >= 10:
            recent_revenue = sum(float(o['order_amount']) for o in recent_orders[-10:])
            previous_revenue = sum(float(o['order_amount']) for o in recent_orders[-20:-10])
            
            if recent_revenue < previous_revenue * 0.9:  # 10% decline
                recommendations.append({
                    'category': 'sales_growth',
                    'priority': 'medium',
                    'title': 'Boost Sales Performance',
                    'description': 'Your recent sales show a declining trend compared to previous period.',
                    'actions': [
                        'Review pricing strategy against competitors',
                        'Enhance product listings with better keywords',
                        'Consider promotional campaigns',
                        'Analyze customer feedback for improvement opportunities'
                    ],
                    'expected_impact': 'Could increase revenue by 15-25%'
                })
        
        # Customer satisfaction
        recent_feedback = historical_data.get('feedback', [])
        if recent_feedback:
            avg_rating = np.mean([f['rating'] for f in recent_feedback])
            if avg_rating < 4.0:
                recommendations.append({
                    'category': 'customer_satisfaction',
                    'priority': 'high',
                    'title': 'Improve Customer Satisfaction',
                    'description': f'Your average rating is {avg_rating:.1f}, which is below the recommended 4.0+.',
                    'actions': [
                        'Respond promptly to customer inquiries',
                        'Implement a quality assurance process',
                        'Follow up with customers after delivery',
                        'Address negative feedback proactively'
                    ],
                    'expected_impact': 'Could improve performance score by 12-18 points'
                })
        
        return recommendations
    
    def _calculate_health_score(self, seller: Seller, historical_data: Dict) -> float:
        """Calculate overall seller health score (0-100)."""
        orders = historical_data['orders']
        if not orders:
            return float(seller.performance_score)
        
        scores = []
        
        # Delivery performance (25% weight)
        delivery_times = [o['delivery_days'] for o in orders if o['delivery_days']]
        if delivery_times:
            avg_delivery = np.mean(delivery_times)
            delivery_score = max(0, 100 - (avg_delivery - 2) * 10)  # Optimal is 2 days
            scores.append(delivery_score * 0.25)
        
        # Return rate (25% weight)
        return_rate = sum(1 for o in orders if o['is_returned']) / len(orders) * 100
        return_score = max(0, 100 - return_rate * 5)  # Penalize high return rates
        scores.append(return_score * 0.25)
        
        # Revenue trend (25% weight)
        if len(orders) >= 10:
            recent_revenue = sum(float(o['order_amount']) for o in orders[-5:])
            previous_revenue = sum(float(o['order_amount']) for o in orders[-10:-5])
            revenue_growth = (recent_revenue - previous_revenue) / previous_revenue if previous_revenue > 0 else 0
            revenue_score = 50 + min(50, revenue_growth * 100)  # Scale growth to score
            scores.append(revenue_score * 0.25)
        
        # Current performance score (25% weight)
        scores.append(float(seller.performance_score) * 0.25)
        
        return max(0, min(100, sum(scores)))
    
    def _identify_risk_factors(self, seller: Seller, historical_data: Dict) -> List[str]:
        """Identify potential risk factors affecting seller performance."""
        risk_factors = []
        orders = historical_data['orders']
        
        if not orders:
            risk_factors.append("Insufficient order history for risk assessment")
            return risk_factors
        
        # Check for declining trends
        if len(orders) >= 10:
            recent_orders = orders[-5:]
            previous_orders = orders[-10:-5]
            
            recent_revenue = sum(float(o['order_amount']) for o in recent_orders)
            previous_revenue = sum(float(o['order_amount']) for o in previous_orders)
            
            if recent_revenue < previous_revenue * 0.8:
                risk_factors.append("Significant revenue decline detected")
        
        # Check delivery performance
        delivery_times = [o['delivery_days'] for o in orders if o['delivery_days']]
        if delivery_times and np.mean(delivery_times) > 7:
            risk_factors.append("Above average delivery times")
        
        # Check return rate
        return_rate = sum(1 for o in orders if o['is_returned']) / len(orders) * 100
        if return_rate > 15:
            risk_factors.append("High return rate indicating quality issues")
        
        # Check order frequency
        if len(orders) < 10 and len(orders) > 0:
            days_span = (max(o['order_date'] for o in orders) - min(o['order_date'] for o in orders)).days
            if days_span > 30:  # Less than 10 orders in more than 30 days
                risk_factors.append("Low order frequency")
        
        return risk_factors
    
    def _create_insights_from_analysis(self, seller: Seller, analysis: Dict):
        """Create PerformanceInsight records based on analysis results."""
        from decimal import Decimal
        
        try:
            # Ensure analysis is valid
            if not analysis or 'error' in analysis:
                logger.warning(f"Invalid analysis for seller {seller.id}: {analysis}")
                return
            
            # Create a primary insight summarizing overall health
            health_score = analysis.get('overall_health_score', Decimal('0.00'))
            risk_factors = analysis.get('risk_factors', [])
            
            # Primary health insight
            if health_score >= 80:
                insight_title = 'Excellent Performance'
                severity = PerformanceInsight.Severity.INFO
                desc = "Your metrics are strong across all categories."
                recommendation = "Maintain your current performance level and look for optimization opportunities."
            elif health_score >= 60:
                insight_title = 'Good Performance'
                severity = PerformanceInsight.Severity.INFO
                desc = "Your performance is solid with room for improvement."
                recommendation = "Focus on areas with lower scores to boost overall performance."
            else:
                insight_title = 'Performance Alert'
                severity = PerformanceInsight.Severity.HIGH
                desc = "Your performance metrics need immediate attention."
                recommendation = "Review all metrics and take corrective action in weak areas."
            
            PerformanceInsight.objects.update_or_create(
                seller=seller,
                insight_type=PerformanceInsight.InsightType.PERFORMANCE_ALERT,
                title=insight_title,
                defaults={
                    'severity': severity,
                    'description': desc,
                    'confidence_score': Decimal(min(health_score, 100)),
                    'analysis_data': analysis,
                    'status': PerformanceInsight.Status.ACTIVE,
                    'recommendation': recommendation
                }
            )
            logger.info(f"Created primary health insight for seller {seller.id}")
            
            # Create trend analysis insight
            trend_analysis = analysis.get('trend_analysis', {})
            if trend_analysis and 'error' not in trend_analysis:
                rev_trend = trend_analysis.get('revenue_trend', {})
                if rev_trend and rev_trend.get('slope', 0) > 0:
                    PerformanceInsight.objects.update_or_create(
                        seller=seller,
                        insight_type=PerformanceInsight.InsightType.TREND_ANALYSIS,
                        title='Revenue Growing',
                        defaults={
                            'severity': PerformanceInsight.Severity.INFO,
                            'description': "Your revenue is trending upward! Keep up the good work.",
                            'confidence_score': Decimal('85.00'),
                            'analysis_data': rev_trend,
                            'status': PerformanceInsight.Status.ACTIVE,
                            'recommendation': 'Maintain current strategy and consider scaling operations.'
                        }
                    )
                elif rev_trend:
                    PerformanceInsight.objects.update_or_create(
                        seller=seller,
                        insight_type=PerformanceInsight.InsightType.TREND_ANALYSIS,
                        title='Revenue Declining',
                        defaults={
                            'severity': PerformanceInsight.Severity.HIGH,
                            'description': "Your revenue is declining. Take action to reverse this trend.",
                            'confidence_score': Decimal('80.00'),
                            'analysis_data': rev_trend,
                            'status': PerformanceInsight.Status.ACTIVE,
                            'recommendation': 'Review marketing strategy and consider promotions or improvements.'
                        }
                    )
                logger.info(f"Created trend insight for seller {seller.id}")
            
            # Create recommendations insights
            recommendations = analysis.get('recommendations', [])
            if recommendations:
                rec_str = '\n'.join([str(r) for r in recommendations[:3]])
                PerformanceInsight.objects.update_or_create(
                    seller=seller,
                    insight_type=PerformanceInsight.InsightType.RECOMMENDATION,
                    title='Action Items',
                    defaults={
                        'severity': PerformanceInsight.Severity.MEDIUM,
                        'description': "Here are recommended actions to improve your performance.",
                        'confidence_score': Decimal('75.00'),
                        'analysis_data': {'recommendations': recommendations},
                        'status': PerformanceInsight.Status.ACTIVE,
                        'recommendation': rec_str
                    }
                )
                logger.info(f"Created recommendation insight for seller {seller.id}")
            
            # Create recommendation insights
            if 'recommendations' in analysis:
                for idx, rec in enumerate(analysis['recommendations'][:5]):
                    severity = PerformanceInsight.Severity.HIGH if rec.get('priority') == 'high' else PerformanceInsight.Severity.MEDIUM
                    PerformanceInsight.objects.create(
                        seller=seller,
                        insight_type=PerformanceInsight.InsightType.RECOMMENDATION,
                        severity=severity,
                        title=rec.get('title', 'Recommendation'),
                        description=rec.get('description', ''),
                        recommendation='\n'.join(rec.get('actions', [])),
                        confidence_score=Decimal('85.00'),
                        analysis_data=rec,
                        status=PerformanceInsight.Status.ACTIVE
                    )
            
        except Exception as e:
            logger.error(f"Failed to create insights for seller {seller.id}: {e}")
    
    def _generate_trend_description(self, trends: Dict) -> str:
        """Generate human-readable trend description."""
        descriptions = []
        
        if 'revenue_trend' in trends:
            direction = trends['revenue_trend']['direction']
            descriptions.append(f"Revenue is {direction}")
        
        if 'order_trend' in trends:
            direction = trends['order_trend']['direction']
            descriptions.append(f"Order volume is {direction}")
        
        if 'return_rate_trend' in trends:
            direction = trends['return_rate_trend']['direction']
            descriptions.append(f"Return rate is {direction}")
        
        return ". ".join(descriptions) + "."
    
    def _create_predictive_alert(self, seller: Seller, alert_type: str, predictions: Dict):
        """Create predictive alert for concerning predictions."""
        try:
            alert_messages = {
                'performance_decline': f"Performance score predicted to drop to {predictions['predicted_performance_score']:.1f}",
                'return_rate_spike': "Return rate is trending upward",
                'delivery_delay_risk': "Delivery times are increasing"
            }
            
            PredictiveAlert.objects.create(
                seller=seller,
                alert_type=alert_type,
                priority=PredictiveAlert.Priority.HIGH,
                title=f"Predictive Alert: {alert_type.replace('_', ' ').title()}",
                message=alert_messages.get(alert_type, "Performance concern detected"),
                predicted_metric="performance_score",
                current_value=float(seller.performance_score),
                predicted_value=predictions['predicted_performance_score'],
                confidence_level=predictions['confidence_level'],
                prediction_date=timezone.now() + timedelta(days=30)
            )
            
        except Exception as e:
            logger.error(f"Failed to create predictive alert for seller {seller.id}: {e}")
    
    def generate_ranking_summary(self, seller: Seller, old_rank: int, new_rank: int) -> str:
        """Generate AI summary for ranking changes."""
        try:
            rank_change = old_rank - new_rank  # Positive = moved up
            
            # Analyze recent performance changes
            recent_analysis = self.analyze_seller_performance(seller)
            
            summary_parts = []
            
            if rank_change > 0:
                summary_parts.append(f"Seller moved up {rank_change} positions")
            elif rank_change < 0:
                summary_parts.append(f"Seller moved down {abs(rank_change)} positions")
            else:
                summary_parts.append("Seller maintained their ranking")
            
            # Add specific reasons based on analysis
            if 'trend_analysis' in recent_analysis:
                trends = recent_analysis['trend_analysis']
                
                if trends.get('revenue_trend', {}).get('direction') == 'improving':
                    summary_parts.append("due to increasing sales revenue")
                elif trends.get('return_rate_trend', {}).get('direction') == 'improving':
                    summary_parts.append("due to improved return rate performance")
            
            # Add health score context
            health_score = recent_analysis.get('overall_health_score', 0)
            if health_score > 80:
                summary_parts.append("with strong overall health metrics")
            elif health_score < 60:
                summary_parts.append("with concerning performance indicators")
            
            return ". ".join(summary_parts) + "."
            
        except Exception as e:
            logger.error(f"Failed to generate ranking summary for seller {seller.id}: {e}")
            return f"Ranking changed from position {old_rank} to {new_rank}."
"""Machine Learning Signal Predictor"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import logging
from collections import deque

logger = logging.getLogger(__name__)

class MLSignalPredictor:
    """Machine Learning-based signal prediction"""
    
    def __init__(self, config):
        self.config = config
        self.lookback_periods = int(config.get('ML_LOOKBACK', '50'))
        self.confidence_threshold = float(config.get('ML_CONFIDENCE_THRESHOLD', '0.65'))
        
        # Store recent patterns for learning
        self.pattern_memory = deque(maxlen=500)
        self.successful_patterns = {}
        
        # Feature weights (will be updated through learning)
        self.feature_weights = {
            'rsi_divergence': 0.15,
            'macd_strength': 0.15,
            'volume_spike': 0.10,
            'trend_strength': 0.20,
            'volatility_regime': 0.10,
            'support_resistance': 0.15,
            'momentum_score': 0.15
        }
    
    def analyze(self, symbol: str, mtf_data: Dict, current_price: float) -> Dict:
        """Analyze and predict signal quality"""
        
        # Extract features
        features = self.extract_features(symbol, mtf_data, current_price)
        
        # Calculate pattern match score
        pattern_score = self.match_historical_patterns(features)
        
        # Calculate feature score
        feature_score = self.calculate_feature_score(features)
        
        # Combine scores
        final_score = (pattern_score * 0.4) + (feature_score * 0.6)        
        # Determine confidence
        confidence = self.calculate_confidence(features, final_score)
        
        # Generate prediction
        prediction = self.generate_prediction(final_score, confidence)
        
        return {
            'prediction': prediction,
            'confidence': confidence,
            'pattern_score': pattern_score,
            'feature_score': feature_score,
            'final_score': final_score,
            'features': features,
            'recommended_action': self.get_recommended_action(prediction, confidence)
        }
    
    def extract_features(self, symbol: str, mtf_data: Dict, current_price: float) -> Dict:
        """Extract features from market data"""
        features = {}
        
        # RSI features
        rsi_5m = mtf_data.get('timeframes', {}).get('5m', {}).get('rsi', 50)
        rsi_15m = mtf_data.get('timeframes', {}).get('15m', {}).get('rsi', 50)
        rsi_1h = mtf_data.get('timeframes', {}).get('1h', {}).get('rsi', 50)
        
        features['rsi_avg'] = (rsi_5m + rsi_15m + rsi_1h) / 3
        features['rsi_divergence'] = abs(rsi_5m - rsi_1h) / 100
        features['rsi_oversold'] = 1 if rsi_1h < 35 else 0
        features['rsi_overbought'] = 1 if rsi_1h > 65 else 0
        
        # MACD features
        macd_1h = mtf_data.get('timeframes', {}).get('1h', {}).get('macd_signal', 0)
        features['macd_strength'] = abs(macd_1h) if macd_1h != 0 else 0
        features['macd_bullish'] = 1 if macd_1h > 0 else 0
        
        # Volume features
        volume_5m = mtf_data.get('timeframes', {}).get('5m', {}).get('volume', 0)
        volume_1h = mtf_data.get('timeframes', {}).get('1h', {}).get('volume', 0)
        features['volume_spike'] = 1 if volume_5m > (volume_1h * 0.3) else 0
        
        # Trend features
        score = mtf_data.get('score', 50)
        features['trend_strength'] = abs(score - 50) / 50
        features['trend_direction'] = 1 if score > 50 else 0
        
        # Volatility features
        volatility = mtf_data.get('timeframes', {}).get('1h', {}).get('volatility', 'NORMAL')
        features['volatility_regime'] = 1 if volatility == 'HIGH' else (0.5 if volatility == 'NORMAL' else 0)
                # Momentum features
        momentum_aligned = mtf_data.get('details', {}).get('momentum_alignment', False)
        features['momentum_score'] = 1 if momentum_aligned else 0
        
        # Support/Resistance proximity (simplified)
        features['support_resistance'] = 0.5  # Will be enhanced later
        
        return features
    
    def calculate_feature_score(self, features: Dict) -> float:
        """Calculate weighted feature score"""
        score = 0
        total_weight = 0
        
        for feature_name, feature_value in features.items():
            weight = self.feature_weights.get(feature_name, 0.1)
            score += feature_value * weight
            total_weight += weight
        
        return (score / total_weight) * 100 if total_weight > 0 else 50
    
    def match_historical_patterns(self, features: Dict) -> float:
        """Match current features against historical successful patterns"""
        if not self.successful_patterns:
            return 50  # Neutral if no history
        
        best_match_score = 0
        best_match_count = 0
        
        for pattern_id, pattern_data in self.successful_patterns.items():
            similarity = self.calculate_similarity(features, pattern_data['features'])
            if similarity > 0.7:  # 70% similarity threshold
                best_match_score += pattern_data['success_rate']
                best_match_count += 1
        
        if best_match_count == 0:
            return 50
        
        return (best_match_score / best_match_count) * 100
    
    def calculate_similarity(self, features1: Dict, features2: Dict) -> float:
        """Calculate similarity between two feature sets"""
        if not features1 or not features2:
            return 0
        
        matching_features = 0
        total_features = 0
        
        for feature_name in features1.keys():
            if feature_name in features2:                val1 = features1[feature_name]
                val2 = features2[feature_name]
                
                # Normalize comparison
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    diff = abs(val1 - val2)
                    if diff < 0.1:
                        matching_features += 1
                    elif diff < 0.3:
                        matching_features += 0.5
                
                total_features += 1
        
        return matching_features / total_features if total_features > 0 else 0
    
    def calculate_confidence(self, features: Dict, score: float) -> float:
        """Calculate confidence in the prediction"""
        confidence_factors = []
        
        # Feature completeness
        completeness = len([f for f in features.values() if f is not None]) / len(features)
        confidence_factors.append(completeness)
        
        # Score extremity (more extreme = more confident)
        extremity = abs(score - 50) / 50
        confidence_factors.append(extremity)
        
        # Momentum alignment
        if features.get('momentum_score', 0) > 0.5:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.5)
        
        # Trend strength
        trend_strength = features.get('trend_strength', 0)
        confidence_factors.append(trend_strength)
        
        # Average confidence
        confidence = sum(confidence_factors) / len(confidence_factors)
        
        return min(max(confidence, 0), 1)  # Clamp between 0 and 1
    
    def generate_prediction(self, score: float, confidence: float) -> str:
        """Generate prediction based on score and confidence"""
        if confidence < self.confidence_threshold:
            return 'UNCERTAIN'
        
        if score >= 75:
            return 'STRONG_BUY'
        elif score >= 65:            return 'BUY'
        elif score >= 35:
            return 'NEUTRAL'
        elif score >= 25:
            return 'SELL'
        else:
            return 'STRONG_SELL'
    
    def get_recommended_action(self, prediction: str, confidence: float) -> str:
        """Get recommended action"""
        if prediction in ['STRONG_BUY', 'BUY'] and confidence >= 0.7:
            return 'EXECUTE_LONG'
        elif prediction in ['STRONG_SELL', 'SELL'] and confidence >= 0.7:
            return 'EXECUTE_SHORT'
        elif confidence < 0.5:
            return 'WAIT'
        else:
            return 'MONITOR'
    
    def learn_from_trade(self, symbol: str, features: Dict, outcome: str, profit_loss: float):
        """Learn from trade outcome"""
        pattern_id = f"{symbol}_{len(self.pattern_memory)}"
        
        # Determine success
        is_successful = profit_loss > 0
        
        # Store pattern
        self.pattern_memory.append({
            'pattern_id': pattern_id,
            'features': features,
            'outcome': outcome,
            'profit_loss': profit_loss,
            'timestamp': pd.Timestamp.now()
        })
        
        # Update successful patterns
        if is_successful:
            if pattern_id not in self.successful_patterns:
                self.successful_patterns[pattern_id] = {
                    'features': features,
                    'success_count': 0,
                    'total_count': 0,
                    'total_profit': 0
                }
            
            self.successful_patterns[pattern_id]['success_count'] += 1
            self.successful_patterns[pattern_id]['total_count'] += 1
            self.successful_patterns[pattern_id]['total_profit'] += profit_loss
            
            # Update success rate            sp = self.successful_patterns[pattern_id]
            sp['success_rate'] = sp['success_count'] / sp['total_count']
        
        logger.info(f"[ML] Learned from {symbol}: P&L={profit_loss:.2f}, Success={is_successful}")
    
    def get_learning_stats(self) -> Dict:
        """Get statistics about learning"""
        if not self.successful_patterns:
            return {'patterns_learned': 0, 'avg_success_rate': 0}
        
        total_patterns = len(self.successful_patterns)
        avg_success_rate = sum(p['success_rate'] for p in self.successful_patterns.values()) / total_patterns
        
        return {
            'patterns_learned': total_patterns,
            'avg_success_rate': avg_success_rate * 100,
            'total_trades': sum(p['total_count'] for p in self.successful_patterns.values()),
            'successful_trades': sum(p['success_count'] for p in self.successful_patterns.values())
        }

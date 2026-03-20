"""Pattern Recognition Engine"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class PatternRecognizer:
    """Recognizes candlestick and chart patterns"""
    
    def __init__(self):
        self.patterns_detected = []
    
    def detect_all_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect all patterns in dataframe"""
        patterns = {}
        
        # Candlestick patterns
        patterns['doji'] = self.detect_doji(df)
        patterns['hammer'] = self.detect_hammer(df)
        patterns['engulfing'] = self.detect_engulfing(df)
        patterns['morning_star'] = self.detect_morning_star(df)
        patterns['evening_star'] = self.detect_evening_star(df)
        
        # Chart patterns
        patterns['support_level'] = self.detect_support(df)
        patterns['resistance_level'] = self.detect_resistance(df)
        patterns['trend_line'] = self.detect_trend_line(df)
        
        # Calculate pattern strength
        patterns['overall_strength'] = self.calculate_pattern_strength(patterns)
        
        return patterns
    
    def detect_doji(self, df: pd.DataFrame) -> Dict:
        """Detect Doji pattern"""
        if len(df) < 2:
            return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
        
        latest = df.iloc[-1]
        body = abs(latest['close'] - latest['open'])
        range_size = latest['high'] - latest['low']
        
        # Doji: body is very small compared to range
        is_doji = body < (range_size * 0.1) if range_size > 0 else False
        
        if is_doji:            # Check previous trend
            prev_candle = df.iloc[-2]
            if prev_candle['close'] > prev_candle['open']:  # Previous was bullish
                return {'detected': True, 'signal': 'BEARISH', 'strength': 0.7}
            else:
                return {'detected': True, 'signal': 'BULLISH', 'strength': 0.7}
        
        return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
    
    def detect_hammer(self, df: pd.DataFrame) -> Dict:
        """Detect Hammer pattern"""
        if len(df) < 2:
            return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
        
        latest = df.iloc[-1]
        body = abs(latest['close'] - latest['open'])
        upper_shadow = latest['high'] - max(latest['open'], latest['close'])
        lower_shadow = min(latest['open'], latest['close']) - latest['low']
        
        # Hammer: small body, long lower shadow, little/no upper shadow
        is_hammer = (lower_shadow > body * 2 and 
                     upper_shadow < body * 0.5 and
                     latest['close'] > latest['open'])  # Bullish hammer
        
        if is_hammer:
            return {'detected': True, 'signal': 'BULLISH', 'strength': 0.8}
        
        return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
    
    def detect_engulfing(self, df: pd.DataFrame) -> Dict:
        """Detect Engulfing pattern"""
        if len(df) < 2:
            return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        current_body = current['close'] - current['open']
        previous_body = previous['open'] - previous['close']
        
        # Bullish engulfing
        if current_body > 0 and previous_body > 0:
            if (current['open'] < previous['close'] and 
                current['close'] > previous['open']):
                return {'detected': True, 'signal': 'BULLISH', 'strength': 0.85}
        
        # Bearish engulfing
        if current_body < 0 and previous_body < 0:
            if (current['open'] > previous['close'] and 
                current['close'] < previous['open']):                return {'detected': True, 'signal': 'BEARISH', 'strength': 0.85}
        
        return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
    
    def detect_morning_star(self, df: pd.DataFrame) -> Dict:
        """Detect Morning Star pattern"""
        if len(df) < 3:
            return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
        
        candle1 = df.iloc[-3]
        candle2 = df.iloc[-2]
        candle3 = df.iloc[-1]
        
        # Morning Star: bearish, small body, bullish
        if (candle1['close'] < candle1['open'] and  # First bearish
            abs(candle2['close'] - candle2['open']) < abs(candle1['close'] - candle1['open']) * 0.5 and
            candle3['close'] > candle3['open'] and  # Third bullish
            candle3['close'] > candle1['open']):     # Closes above first open
            return {'detected': True, 'signal': 'BULLISH', 'strength': 0.9}
        
        return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
    
    def detect_evening_star(self, df: pd.DataFrame) -> Dict:
        """Detect Evening Star pattern"""
        if len(df) < 3:
            return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
        
        candle1 = df.iloc[-3]
        candle2 = df.iloc[-2]
        candle3 = df.iloc[-1]
        
        # Evening Star: bullish, small body, bearish
        if (candle1['close'] > candle1['open'] and  # First bullish
            abs(candle2['close'] - candle2['open']) < abs(candle1['close'] - candle1['open']) * 0.5 and
            candle3['close'] < candle3['open'] and  # Third bearish
            candle3['close'] < candle1['open']):     # Closes below first open
            return {'detected': True, 'signal': 'BEARISH', 'strength': 0.9}
        
        return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
    
    def detect_support(self, df: pd.DataFrame) -> Dict:
        """Detect support level"""
        if len(df) < 20:
            return {'detected': False, 'level': 0, 'strength': 0}
        
        recent_lows = df['low'].tail(20)
        current_price = df.iloc[-1]['close']
        
        # Find significant lows
        support_level = recent_lows.min()        distance_pct = ((current_price - support_level) / support_level) * 100
        
        # If price is within 2% of support
        if distance_pct < 2 and distance_pct >= 0:
            return {'detected': True, 'level': support_level, 'strength': 0.8}
        
        return {'detected': False, 'level': support_level, 'strength': 0}
    
    def detect_resistance(self, df: pd.DataFrame) -> Dict:
        """Detect resistance level"""
        if len(df) < 20:
            return {'detected': False, 'level': 0, 'strength': 0}
        
        recent_highs = df['high'].tail(20)
        current_price = df.iloc[-1]['close']
        
        # Find significant highs
        resistance_level = recent_highs.max()
        distance_pct = ((resistance_level - current_price) / current_price) * 100
        
        # If price is within 2% of resistance
        if distance_pct < 2 and distance_pct >= 0:
            return {'detected': True, 'level': resistance_level, 'strength': 0.8}
        
        return {'detected': False, 'level': resistance_level, 'strength': 0}
    
    def detect_trend_line(self, df: pd.DataFrame) -> Dict:
        """Detect trend line breakout"""
        if len(df) < 50:
            return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
        
        # Simple trend detection using linear regression
        closes = df['close'].tail(50).values
        x = np.arange(len(closes))
        slope = np.polyfit(x, closes, 1)[0]
        
        current_price = df.iloc[-1]['close']
        avg_price = np.mean(closes)
        
        # Calculate trend strength
        trend_strength = abs(slope) / avg_price
        
        if trend_strength > 0.001:  # Significant trend
            if slope > 0:
                return {'detected': True, 'signal': 'BULLISH', 'strength': min(trend_strength * 100, 1)}
            else:
                return {'detected': True, 'signal': 'BEARISH', 'strength': min(trend_strength * 100, 1)}
        
        return {'detected': False, 'signal': 'NEUTRAL', 'strength': 0}
        def calculate_pattern_strength(self, patterns: Dict) -> float:
        """Calculate overall pattern strength"""
        bullish_signals = 0
        bearish_signals = 0
        total_strength = 0
        
        for pattern_name, pattern_data in patterns.items():
            if pattern_name == 'overall_strength':
                continue
            
            if pattern_data.get('detected', False):
                strength = pattern_data.get('strength', 0)
                total_strength += strength
                
                if pattern_data.get('signal') == 'BULLISH':
                    bullish_signals += strength
                elif pattern_data.get('signal') == 'BEARISH':
                    bearish_signals += strength
        
        # Net signal
        if bullish_signals > bearish_signals:
            return min(total_strength, 1)
        elif bearish_signals > bullish_signals:
            return -min(total_strength, 1)
        else:
            return 0

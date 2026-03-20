"""Multi-Timeframe Analysis Engine"""
import ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class MultiTimeframeAnalyzer:
    """Analyzes multiple timeframes for trend confirmation"""
    
    def __init__(self, exchange, config):
        self.exchange = exchange
        self.config = config
        self.timeframes = ['5m', '15m', '1h', '4h']
        
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol"""
        try:
            bars = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    def analyze_all_timeframes(self, symbol: str) -> Dict:
        """Analyze all timeframes and return combined signal"""
        results = {}
        
        for tf in self.timeframes:
            df = self.get_ohlcv(symbol, tf)
            if df.empty:
                continue
                
            results[tf] = self.analyze_timeframe(df, tf)
        
        return self.combine_signals(results)
    
    def analyze_timeframe(self, df: pd.DataFrame, timeframe: str) -> Dict:
        """Analyze a single timeframe"""
        # Add indicators
        df = self.add_indicators(df)
                # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # Determine trend
        trend = self.determine_trend(df, latest)
        
        # Determine momentum
        momentum = self.determine_momentum(latest, prev)
        
        # Determine volatility
        volatility = self.determine_volatility(df, latest)
        
        # Generate signal
        signal = self.generate_tf_signal(trend, momentum, volatility, latest)
        
        return {
            'trend': trend,
            'momentum': momentum,
            'volatility': volatility,
            'signal': signal,
            'rsi': latest.get('rsi', 50),
            'macd_signal': latest.get('macd_signal', 0),
            'price': latest['close'],
            'volume': latest['volume']
        }
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all technical indicators"""
        # RSI
        df['rsi'] = self.calculate_rsi(df['close'], period=14)
        
        # MACD
        macd, signal, hist = self.calculate_macd(df['close'])
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist
        
        # Bollinger Bands
        upper, middle, lower = self.calculate_bollinger(df['close'])
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        
        # EMA
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # ADX        df['adx'] = self.calculate_adx(df, period=14)
        
        # ATR
        df['atr'] = self.calculate_atr(df, period=14)
        
        # Volume SMA
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, series: pd.Series) -> Tuple:
        """Calculate MACD"""
        exp1 = series.ewm(span=12, adjust=False).mean()
        exp2 = series.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def calculate_bollinger(self, series: pd.Series, period: int = 20) -> Tuple:
        """Calculate Bollinger Bands"""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * 2)
        lower = middle - (std * 2)
        return upper, middle, lower
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX (Average Directional Index)"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = self.calculate_true_range(df)
        atr = tr.rolling(window=period).mean()
                plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """Calculate True Range"""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        tr = self.calculate_true_range(df)
        return tr.rolling(window=period).mean()
    
    def determine_trend(self, df: pd.DataFrame, latest: pd.Series) -> str:
        """Determine overall trend"""
        ema_9 = latest['ema_9']
        ema_21 = latest['ema_21']
        ema_50 = latest['ema_50']
        price = latest['close']
        
        # Strong uptrend
        if price > ema_9 > ema_21 > ema_50:
            return 'STRONG_UPTREND'
        # Uptrend
        elif price > ema_21 and ema_9 > ema_21:
            return 'UPTREND'
        # Strong downtrend
        elif price < ema_9 < ema_21 < ema_50:
            return 'STRONG_DOWNTREND'
        # Downtrend
        elif price < ema_21 and ema_9 < ema_21:
            return 'DOWNTREND'
        # Sideways
        else:
            return 'SIDEWAYS'
    
    def determine_momentum(self, latest: pd.Series, prev: pd.Series) -> str:
        """Determine momentum"""        rsi = latest['rsi']
        macd = latest['macd']
        macd_signal = latest['macd_signal']
        
        # Strong bullish momentum
        if rsi > 50 and rsi < 70 and macd > macd_signal:
            return 'BULLISH'
        # Strong bearish momentum
        elif rsi < 50 and rsi > 30 and macd < macd_signal:
            return 'BEARISH'
        # Overbought
        elif rsi >= 70:
            return 'OVERBOUGHT'
        # Oversold
        elif rsi <= 30:
            return 'OVERSOLD'
        # Weak
        else:
            return 'WEAK'
    
    def determine_volatility(self, df: pd.DataFrame, latest: pd.Series) -> str:
        """Determine volatility regime"""
        atr = latest['atr']
        price = latest['close']
        atr_pct = (atr / price) * 100
        
        if atr_pct > 3:
            return 'HIGH'
        elif atr_pct < 1:
            return 'LOW'
        else:
            return 'NORMAL'
    
    def generate_tf_signal(self, trend: str, momentum: str, volatility: str, latest: pd.Series) -> str:
        """Generate signal for this timeframe"""
        # Strong buy conditions
        if trend in ['STRONG_UPTREND', 'UPTREND'] and momentum in ['BULLISH', 'OVERSOLD']:
            return 'STRONG_BUY'
        elif trend in ['STRONG_UPTREND', 'UPTREND'] and momentum == 'BULLISH':
            return 'BUY'
        
        # Strong sell conditions
        elif trend in ['STRONG_DOWNTREND', 'DOWNTREND'] and momentum in ['BEARISH', 'OVERBOUGHT']:
            return 'STRONG_SELL'
        elif trend in ['STRONG_DOWNTREND', 'DOWNTREND'] and momentum == 'BEARISH':
            return 'SELL'
        
        # Neutral
        else:
            return 'NEUTRAL'    
    def combine_signals(self, results: Dict) -> Dict:
        """Combine signals from all timeframes"""
        if not results:
            return {'signal': 'NEUTRAL', 'score': 50, 'details': {}}
        
        # Weight timeframes (higher timeframes more important)
        weights = {'5m': 1, '15m': 2, '1h': 3, '4h': 4}
        
        total_score = 0
        total_weight = 0
        
        signal_map = {
            'STRONG_BUY': 100,
            'BUY': 75,
            'NEUTRAL': 50,
            'SELL': 25,
            'STRONG_SELL': 0
        }
        
        for tf, data in results.items():
            weight = weights.get(tf, 1)
            score = signal_map.get(data['signal'], 50)
            total_score += score * weight
            total_weight += weight
        
        final_score = total_score / total_weight if total_weight > 0 else 50
        
        # Determine final signal
        if final_score >= 80:
            final_signal = 'STRONG_BUY'
        elif final_score >= 65:
            final_signal = 'BUY'
        elif final_score >= 35:
            final_signal = 'NEUTRAL'
        elif final_score >= 20:
            final_signal = 'SELL'
        else:
            final_signal = 'STRONG_SELL'
        
        return {
            'signal': final_signal,
            'score': final_score,
            'timeframes': results,
            'details': {
                'higher_tf_bias': results.get('4h', {}).get('trend', 'UNKNOWN'),
                'momentum_alignment': self.check_momentum_alignment(results)
            }
        }
        def check_momentum_alignment(self, results: Dict) -> bool:
        """Check if momentum aligns across timeframes"""
        if len(results) < 2:
            return False
        
        signals = [data['signal'] for data in results.values()]
        
        # Check if majority agree
        buy_signals = sum(1 for s in signals if s in ['BUY', 'STRONG_BUY'])
        sell_signals = sum(1 for s in signals if s in ['SELL', 'STRONG_SELL'])
        
        total = len(signals)
        return (buy_signals >= total * 0.6) or (sell_signals >= total * 0.6)

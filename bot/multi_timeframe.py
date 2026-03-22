"""Multi-Timeframe Analysis Module"""
import pandas as pd
from typing import Dict, Optional
import ccxt
import time

class MultiTimeframeAnalyzer:
    """Multi-timeframe analysis for trading signals"""
    
    def __init__(self, exchange, config):
        """Initialize MTF analyzer"""
        self.exchange = exchange
        self.config = config
        self.timeframes = ['15m', '1h', '4h', '1d']
    
    def analyze_all_timeframes(self, symbol: str) -> Optional[Dict]:
        """Analyze all timeframes for a symbol"""
        try:
            results = {}
            for tf in self.timeframes:
                result = self.analyze_timeframe(symbol, tf)
                if result:
                    results[tf] = result
                time.sleep(0.5)
            
            if not results:
                return None
            
            combined = self.combine_timeframe_results(results)
            return combined
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None
    
    def analyze_timeframe(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Analyze a single timeframe"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            if not ohlcv or len(ohlcv) < 20:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df = self.calculate_indicators(df)
            signal = self.get_signal(df)
                        return {
                'timeframe': timeframe,
                'signal': signal,
                'indicators': {
                    'rsi': df['rsi'].iloc[-1] if 'rsi' in df.columns else 50,
                    'macd': df['macd'].iloc[-1] if 'macd' in df.columns else 0,
                }
            }
            
        except Exception as e:
            print(f"Error analyzing {symbol} {timeframe}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        return df
    
    def get_signal(self, df: pd.DataFrame) -> str:
        """Get trading signal from indicators"""
        try:
            rsi = df['rsi'].iloc[-1]
            macd = df['macd'].iloc[-1]
            macd_signal = df['macd_signal'].iloc[-1]
            
            if rsi < 30 and macd > macd_signal:
                return 'STRONG_BUY'
            if rsi < 40 or (macd > macd_signal and rsi < 50):
                return 'BUY'
            if rsi > 70 and macd < macd_signal:
                return 'STRONG_SELL'
            if rsi > 60 or (macd < macd_signal and rsi > 50):
                return 'SELL'
            
            return 'NEUTRAL'
            
        except Exception as e:
            print(f"Error getting signal: {e}")
            return 'NEUTRAL'
        def combine_timeframe_results(self, results: Dict) -> Dict:
        """Combine results from all timeframes"""
        try:
            signals = [data.get('signal', 'NEUTRAL') for data in results.values()]
            buy_count = sum(1 for s in signals if s in ['BUY', 'STRONG_BUY'])
            sell_count = sum(1 for s in signals if s in ['SELL', 'STRONG_SELL'])
            total = len(signals)
            
            if buy_count >= total * 0.6:
                overall_signal = 'BUY'
            elif sell_count >= total * 0.6:
                overall_signal = 'SELL'
            else:
                overall_signal = 'NEUTRAL'
            
            score = 50
            if overall_signal == 'BUY':
                score = 50 + (buy_count / total) * 50
            elif overall_signal == 'SELL':
                score = 50 - (sell_count / total) * 50
            
            return {
                'signal': overall_signal,
                'score': score,
                'timeframe_signals': results,
                'details': {
                    'buy_count': buy_count,
                    'sell_count': sell_count,
                    'total': total,
                    'momentum_alignment': buy_count >= 3 or sell_count >= 3
                }
            }
            
        except Exception as e:
            print(f"Error combining results: {e}")
            return {'signal': 'NEUTRAL', 'score': 50, 'timeframe_signals': results}
    
    def check_momentum_alignment(self, results: Dict) -> bool:
        """Check if momentum aligns across timeframes"""
        if len(results) < 2:
            return False
        
        signals = [data.get('signal', 'NEUTRAL') for data in results.values()]
        buy_signals = sum(1 for s in signals if s in ['BUY', 'STRONG_BUY'])
        sell_signals = sum(1 for s in signals if s in ['SELL', 'STRONG_SELL'])
        total = len(signals)
        return (buy_signals >= total * 0.6) or (sell_signals >= total * 0.6)

def get_top_pairs(config=None, limit=50):
    """Standalone function to get top trading pairs"""    try:
        from bot.config_loader import load_config
        from bot.exchange_factory import build_exchange
        from bot.market_scanner import MarketScanner
        
        if config is None:
            config = load_config()
        
        exchange = build_exchange(config)
        scanner = MarketScanner(config, exchange)
        pairs = scanner.scan_all_markets()
        
        if pairs:
            return pairs[:limit]
        return []
    except Exception as e:
        print(f"Error in get_top_pairs: {e}")
        return []

"""Pair Trader - Enhanced with Multi-Timeframe Analysis"""
import logging
import time

logger = logging.getLogger(__name__)

class PairTrader:
    """Handles trading logic for a single pair"""
    
    def __init__(self, symbol, config, exchange):
        self.symbol = symbol
        self.config = config
        self.exchange = exchange
        self.last_trade_time = 0
        self.cooldown_minutes = int(config.get('BOT_TRADE_COOLDOWN_MIN', '30'))
        
        # Initialize multi-timeframe analyzer
        from bot.multi_timeframe import MultiTimeframeAnalyzer
        self.mtf_analyzer = MultiTimeframeAnalyzer(exchange, config)
        
        # Minimum score to trade (0-100)
        self.min_trade_score = float(config.get('MIN_TRADE_SCORE', '70'))
    
    def trade(self):
        """Attempt to open a new trade on this pair"""
        try:
            # Check cooldown
            minutes_since = (time.time() - self.last_trade_time) / 60
            if minutes_since < self.cooldown_minutes:
                remaining = int(self.cooldown_minutes - minutes_since)
                logger.info(f"[PairTrader] {self.symbol} in cooldown ({remaining}m remaining)")
                return False
            
            # Multi-timeframe analysis
            mtf_result = self.mtf_analyzer.analyze_all_timeframes(self.symbol)
            
            if not mtf_result:
                logger.warning(f"[PairTrader] {self.symbol} - No MTF data available")
                return False
            
            # Check score
            score = mtf_result.get('score', 50)
            signal = mtf_result.get('signal', 'NEUTRAL')
            
            logger.info(f"[PairTrader] {self.symbol} - Score: {score:.1f}, Signal: {signal}")
            
            # Only trade if score is high enough
            if score < self.min_trade_score:                logger.info(f"[PairTrader] {self.symbol} - Score {score:.1f} below threshold {self.min_trade_score}")
            return False
            
            # Check momentum alignment
            if not mtf_result.get('details', {}).get('momentum_alignment', False):
                logger.info(f"[PairTrader] {self.symbol} - Momentum not aligned across timeframes")
                return False
            
            # Get latest price
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            # Determine direction
            if signal in ['STRONG_BUY', 'BUY']:
                direction = 'LONG'
            elif signal in ['STRONG_SELL', 'SELL']:
                direction = 'SHORT'
            else:
                logger.info(f"[PairTrader] {self.symbol} - Neutral signal")
                return False
            
            # Calculate quantity
            qty = self._calc_qty(current_price)
            if not qty or qty <= 0:
                logger.warning(f"[PairTrader] {self.symbol} qty=0, skipping trade")
                return False
            
            # Calculate TP/SL based on ATR
            tp_price, sl_price = self._calculate_tp_sl(current_price, direction)
            
            # Execute order
            logger.info(f"[PairTrader] {self.symbol} --- {direction} {qty} @ {current_price}")
            logger.info(f"[PairTrader] {self.symbol} TP: {tp_price}, SL: {sl_price}")
            
            order = self.exchange.create_market_order(self.symbol, direction.lower(), qty)
            
            if order:
                self.last_trade_time = time.time()
                logger.info(f"[PairTrader] {self.symbol} ✅ ORDER SUCCESS - Score: {score:.1f}")
                return True
            else:
                logger.error(f"[PairTrader] {self.symbol} ❌ ORDER FAILED")
                return False
                
        except Exception as e:
            logger.error(f"[PairTrader] {self.symbol} trade error: {e}")
            return False
    
    def _calculate_tp_sl(self, price: float, direction: str) -> tuple:
        """Calculate Take Profit and Stop Loss based on ATR"""        try:
            # Get ATR from 1h timeframe
            df = self.mtf_analyzer.get_ohlcv(self.symbol, '1h', limit=50)
            if df.empty:
                # Fallback to fixed percentages
                if direction == 'LONG':
                    return price * 1.025, price * 0.985
                else:
                    return price * 0.975, price * 1.015
            
            atr = df.iloc[-1]['atr']
            
            # Use 2x ATR for TP and 1.5x ATR for SL
            if direction == 'LONG':
                tp_price = price + (2 * atr)
                sl_price = price - (1.5 * atr)
            else:
                tp_price = price - (2 * atr)
                sl_price = price + (1.5 * atr)
            
            return round(tp_price, 2), round(sl_price, 2)
            
        except Exception as e:
            logger.error(f"Error calculating TP/SL: {e}")
            if direction == 'LONG':
                return price * 1.025, price * 0.985
            else:
                return price * 0.975, price * 1.015
    
    def _calc_qty(self, price):
        """Calculate position size based on risk settings"""
        try:
            balance = self.exchange.get_balance()
            risk_pct = float(self.config.get('BOT_RISK_PCT', '10.0'))
            max_pos_usd = float(self.config.get('BOT_MAX_POS_USD', '3.0'))
            
            risk_usd = min(balance * (risk_pct / 100), max_pos_usd)
            qty = risk_usd / price
            return round(qty, 2)
        except Exception as e:
            logger.error(f"Error calculating quantity: {e}")
            return 0

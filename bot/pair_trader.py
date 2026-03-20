"""Pair Trader - Handles trading logic for individual pairs"""
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
    
    def trade(self):
        """Attempt to open a new trade on this pair"""
        try:
            # Check cooldown
            minutes_since = (time.time() - self.last_trade_time) / 60
            if minutes_since < self.cooldown_minutes:
                remaining = int(self.cooldown_minutes - minutes_since)
                logger.info(f"[PairTrader] {self.symbol} in cooldown ({remaining}m remaining)")
                return False
            
            # Generate signal
            sig = self.strategy.generate_signal(self.exchange)
            if not sig or sig.direction == "FLAT":
                logger.info(f"[PairTrader] {self.symbol} signal=FLAT - skip")
                return False
            
            # Calculate side and quantity
            side = "buy" if sig.direction == "LONG" else "sell"
            if not qty or qty <= 0:
                logger.warning(f"[PairTrader] {self.symbol} qty=0, skipping trade")
                return False
            
            # Calculate TP/SL
            tp_price = sig.price * 1.025
            sl_price = sig.price * 0.985
            
            # Execute order
            logger.info(f"[PairTrader] {self.symbol} --- Attempting {side.upper()} {qty} @ {sig.price}")
            
            order = self.exchange.create_market_order(self.symbol, side, qty)
            
            if order:
                self.last_trade_time = time.time()
                logger.info(f"[PairTrader] {self.symbol} ORDER SUCCESS - TP: {tp_price}, SL: {sl_price}")
                return True
            else:
                logger.error(f"[PairTrader] {self.symbol} ORDER FAILED")
                return False
                
        except Exception as e:
            logger.error(f"[PairTrader] {self.symbol} trade error: {e}")
            return False
    
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
    
    @property
    def strategy(self):
        """Get trading strategy"""
        from bot.multi_strategy import MultiStrategy
        return MultiStrategy(self.config)

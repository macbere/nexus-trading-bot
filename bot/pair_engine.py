"""Pair Engine - Handles trading on individual pairs"""
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PairEngine:
    """Manages trading on a single pair"""
    
    def __init__(self, config, exchange):
        self.config = config
        self.exchange = exchange
        self.traders = {}
        self.max_open = 3
        logger.info("[PairEngine] Ready - Smart Market Scanner active")
    
    def get_trader(self, symbol):
        """Get or create a PairTrader for a symbol"""
        if isinstance(symbol, dict):
            symbol_str = symbol.get('symbol', str(symbol))
        else:
            symbol_str = str(symbol)
        
        if symbol_str not in self.traders:
            self.traders[symbol_str] = PairTrader(symbol_str, self.config, self.exchange)
        return self.traders[symbol_str]
    
    def count_open(self):
        """Count currently open positions"""
        try:
            positions = __import__("bot.exchange_factory", fromlist=["get_positions"]).get_positions(self.config)
            return sum(1 for p in positions if p.get('symbol') and 'USDT' in p.get('symbol', ''))
        except Exception as e:
            logger.error(f"Error counting positions: {e}")
            return 0
    
    def scan_and_trade(self):
        """Scan pairs and execute trades"""
        try:
            if self.count_open() >= self.max_open:
                logger.info(f"[PairEngine] Max positions ({self.max_open}) reached - skipping")
                return False
            
            # Get top pairs by volume
            top_pairs = __import__("bot.market_scanner", fromlist=["get_top_pairs"]).get_top_pairs(self.config, limit=10)            
            for pair in top_pairs:
                trader = self.get_trader(pair)
                trader.trade()
                time.sleep(2)  # Avoid rate limits
            
            return True
        except Exception as e:
            logger.error(f"[PairEngine] Scan error: {e}")
            return False


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
            qty = self._calc_qty(sig.price)
            if not qty or qty <= 0:
                logger.warning(f"[PairTrader] {self.symbol} qty=0, skipping trade")
                return False
            
            # Execute order
            logger.info(f"[PairTrader] {self.symbol} --- Attempting {side.upper()} {qty} @ {sig.price}")
            
            # Calculate TP/SL
            tp_price = sig.price * 1.025            sl_price = sig.price * 0.985
            
            # Place order (implementation depends on your exchange wrapper)
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

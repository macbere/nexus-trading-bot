"""Pair Engine - Handles trading on individual pairs"""
import logging
import time

logger = logging.getLogger(__name__)

class PairEngine:
    """Manages trading on a single pair"""
    
    def __init__(self, config, exchange):
        self.config = config
        self.exchange = exchange
        self.traders = {}
        self.max_open = 5
        logger.info("[PairEngine] Ready - Smart Market Scanner active")
    
    def get_trader(self, symbol):
        """Get or create a PairTrader for a symbol"""
        if isinstance(symbol, dict):
            symbol_str = symbol.get('symbol', str(symbol))
        else:
            symbol_str = str(symbol)
        
        if symbol_str not in self.traders:
            from bot.pair_trader import PairTrader
            self.traders[symbol_str] = PairTrader(symbol_str, self.config, self.exchange)
        return self.traders[symbol_str]
    
    def count_open(self):
        """Count currently open positions"""
        try:
            positions = self.exchange.fetch_positions()
            return len([p for p in positions if p.get('symbol') and 'USDT' in p.get('symbol', '')])
        except Exception as e:
            logger.error(f"Error counting positions: {e}")
            return 0
    
    def scan_and_trade(self):
        """Scan pairs and execute trades"""
        try:
            if self.count_open() >= self.max_open:
                logger.info("[PairEngine] Max positions ({self.max_open}) reached - skipping")
                return False
            
            from bot.market_scanner import get_top_pairs
            top_pairs = get_top_pairs(self.config, limit=50)            
            for pair in top_pairs:
                trader = self.get_trader(pair)
                trader.trade()
                time.sleep(2)
            
            return True
        except Exception as e:
            logger.error("[PairEngine] Scan error: {e}")
            return False

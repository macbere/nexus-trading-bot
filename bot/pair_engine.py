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
        """Count currently open positions - using open_trades dict"""
        try:
            # Count non-None entries in open_trades
            count = sum(1 for trader in self.traders.values() if trader and hasattr(trader, 'position') and trader.position is not None)
            logger.debug(f"Open positions count: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting positions: {e}")
            # Fallback: just return 0 to allow trading
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
            logger.error(f"[PairEngine] Scan error: {str(e)}")
        logger.error(f"[PairEngine] Full traceback:")
        import traceback
        logger.error(traceback.format_exc())
            return False

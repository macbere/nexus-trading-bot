"""Pair Engine - main orchestration"""
import time
import logging

logger = logging.getLogger(__name__)

class PairEngine:
    def __init__(self, config, exchange):
        self.config = config
        self.exchange = exchange
        self.traders = {}
        self.max_open = 3
        logger.info("[PairEngine] Ready - Smart Market Scanner active")

    def scan_and_trade(self):
        try:
            from bot.market_scanner import MarketScanner
            from bot.pair_trader import PairTrader
            scanner = MarketScanner(self.config, self.exchange)
            top_pairs = scanner.scan_all_markets()
            if not top_pairs:
                logger.info("[PairEngine] No pairs found")
                return False
            for pair in top_pairs:
                if pair not in self.traders:
                    self.traders[pair] = PairTrader(pair, self.exchange, self.config)
                self.traders[pair].trade()
                time.sleep(2)
            return True
        except Exception as e:
            import traceback
            logger.error(f"[PairEngine] Scan error: {str(e)}")
            logger.error(traceback.format_exc())
            return False

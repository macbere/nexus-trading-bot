"""Pair Engine - Main trading orchestration"""
import time
import logging

logger = logging.getLogger(__name__)


class PairEngine:
    def __init__(self, config, exchange):
        self.config = config
        self.exchange = exchange
        self.traders = {}
        self.max_open = int(config.get("BOT_MAX_OPEN_POSITIONS", 2))
        logger.info("[PairEngine] Ready - Smart Market Scanner active")

    def scan_and_trade(self):
        try:
            from bot.market_scanner import MarketScanner
            from bot.pair_trader import PairTrader

            scanner = MarketScanner(self.config, self.config)
            top_pairs = scanner.scan_all_markets()

            if not top_pairs:
                logger.info("[PairEngine] No pairs found")
                return False

            # Check open positions count
            from bot.exchange_factory import get_positions
            open_positions = get_positions(self.config)
            if len(open_positions) >= self.max_open:
                logger.info(
                    f"[PairEngine] Max positions reached "
                    f"({len(open_positions)}/{self.max_open}), skipping"
                )
                return False

            for pair in top_pairs:
                # Get scanner score for this pair
                scanner_score = scanner.scores.get(pair, {}).get("score", 0)

                if pair not in self.traders:
                    self.traders[pair] = PairTrader(
                        pair, self.config, self.config
                    )

                # Pass scanner score directly - skip MTF re-scoring
                self.traders[pair].trade_with_score(scanner_score)
                time.sleep(2)

            return True

        except Exception as e:
            import traceback
            logger.error(f"[PairEngine] Scan error: {e}")
            logger.error(traceback.format_exc())
            return False

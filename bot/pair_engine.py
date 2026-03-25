"""
NEXUS Pair Engine - Final Production Version
- Passes scanner scores AND RSI to pair_trader
- Checks open positions before trading
- No duplicate scanner instances
"""
import time
import logging

logger = logging.getLogger(__name__)


class PairEngine:

    def __init__(self, config, exchange=None):
        self.config = config
        self.traders = {}
        self.max_open = int(config.get("BOT_MAX_OPEN_POSITIONS", 3))
        logger.info("[Engine] PairEngine ready")

    def scan_and_trade(self):
        try:
            from bot.market_scanner import MarketScanner
            from bot.pair_trader import PairTrader
            from bot.exchange_factory import get_positions

            # Check open positions
            open_pos = get_positions(self.config)
            if len(open_pos) >= self.max_open:
                logger.info(
                    f"[Engine] Max positions ({len(open_pos)}/{self.max_open}), "
                    f"skipping"
                )
                return False

            # Scan markets
            scanner = MarketScanner(self.config, self.config)
            top_pairs = scanner.scan_all_markets()

            if not top_pairs:
                logger.info("[Engine] No pairs found")
                return False

            slots_available = self.max_open - len(open_pos)
            traded = 0

            for pair in top_pairs:
                if traded >= slots_available:
                    break

                # Skip if already in open positions
                pair_raw = pair.replace(":USDT", "").replace("/", "")
                already_open = any(
                    pair_raw in p.get("symbol", "")
                    for p in open_pos
                )
                if already_open:
                    logger.info(f"[Engine] {pair} already open, skipping")
                    continue

                score = scanner.scores.get(pair, {}).get("score", 0)
                rsi = scanner.scores.get(pair, {}).get("rsi", 50)

                if pair not in self.traders:
                    self.traders[pair] = PairTrader(pair, self.config)

                result = self.traders[pair].trade_with_score(score, rsi)
                if result:
                    traded += 1
                time.sleep(2)

            return traded > 0

        except Exception as e:
            import traceback
            logger.error(f"[Engine] Error: {e}")
            logger.error(traceback.format_exc())
            return False

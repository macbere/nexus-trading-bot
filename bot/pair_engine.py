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
            from bot.exchange_factory import (
                get_open_orders,
                get_pending_plan_orders,
                get_positions,
            )

            # Check open positions
            open_pos = get_positions(self.config, fail_closed=True)
            if open_pos is None:
                logger.error("[Engine] Cannot verify positions; refusing to trade")
                return False
            open_orders = get_open_orders(self.config, fail_closed=True)
            plan_orders = get_pending_plan_orders(self.config, fail_closed=True)
            if open_orders is None or plan_orders is None:
                logger.error("[Engine] Cannot verify pending orders; refusing to trade")
                return False
            if len(open_pos) >= self.max_open:
                logger.info(
                    f"[Engine] Max positions ({len(open_pos)}/{self.max_open}), "
                    f"skipping"
                )
                return False
            if open_orders or plan_orders:
                logger.info(
                    f"[Engine] Pending orders detected (normal={len(open_orders)}, "
                    f"plan={len(plan_orders)}), skipping new orders"
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

                # Re-check immediately before each order. A previous order
                # may have filled after the initial scan-level snapshot.
                current_positions = get_positions(self.config, fail_closed=True)
                current_orders = get_open_orders(self.config, fail_closed=True)
                current_plan_orders = get_pending_plan_orders(self.config, fail_closed=True)
                if current_positions is None or current_orders is None or current_plan_orders is None:
                    logger.error("[Engine] Cannot recheck pending orders; refusing to trade")
                    break
                if current_orders or current_plan_orders:
                    logger.info(
                        f"[Engine] Pending order appeared (normal={len(current_orders)}, "
                        f"plan={len(current_plan_orders)}), stopping scan"
                    )
                    break
                if len(current_positions) + traded >= self.max_open:
                    logger.info(
                        f"[Engine] Position cap reached before {pair} "
                        f"({len(current_positions) + traded}/{self.max_open}), skipping"
                    )
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

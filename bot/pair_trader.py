"""
NEXUS Pair Trader - Final Production Version
- Uses scanner scores directly
- Correct LONG/SHORT direction based on RSI
- Auto TP/SL on every trade
- Trailing stop compatible
"""
import time
import math
import logging
import requests

logger = logging.getLogger(__name__)


class PairTrader:

    def __init__(self, symbol, config, exchange=None):
        self.symbol = symbol
        self.config = config
        self.last_trade_time = 0
        self.min_score = float(config.get("MIN_TRADE_SCORE", 20))
        self.cooldown_secs = float(
            config.get("BOT_TRADE_COOLDOWN_MIN", 10)
        ) * 60

    # ----------------------------------------------------------
    # PRICE FETCH
    # ----------------------------------------------------------
    def _get_price(self):
                return True            return False

    # ----------------------------------------------------------
    # MAIN ENTRY POINT
    # ----------------------------------------------------------
    def trade_with_score(self, scanner_score, rsi=None):
        """
        Called by PairEngine with scanner score and optional RSI.
        Direction: RSI > 65 -> SHORT | RSI < 35 -> LONG | else -> LONG
        """
        try:
            # Cooldown
            elapsed = time.time() - self.last_trade_time
            if self.last_trade_time > 0 and elapsed < self.cooldown_secs:
                mins = int((self.cooldown_secs - elapsed) / 60)
                logger.info(f"[Trader] {self.symbol} cooldown {mins}m")
                return False

            score = float(scanner_score)
            logger.info(f"[Trader] {self.symbol} | Score:{score:.1f}")

            if score < self.min_score:
                logger.info(
                    f"[Trader] {self.symbol} score {score:.1f} "
                    f"< threshold {self.min_score}, skip"
                )
                return False

            # Get price
            price = self._get_price()
            if not price:
                return False

            # Determine direction from RSI
            if rsi is None:
                rsi = self._get_rsi()

            if rsi >= 65:
                direction = "sell"
                dir_label = "SHORT"
            else:
                direction = "buy"
                dir_label = "LONG"

            logger.info(
                f"[Trader] {self.symbol} | RSI:{rsi} | "
                f"{dir_label} @ {price} | Score:{score:.1f}"
            )

            return self._execute(direction, price)

        except Exception as e:
            import traceback
            logger.error(f"[Trader] {self.symbol} error: {e}")
            logger.error(traceback.format_exc())
            return False

    def trade(self):
        """Legacy fallback"""
        return self.trade_with_score(self.min_score + 1)

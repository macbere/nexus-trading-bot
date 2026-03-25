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
        try:
            raw = self.symbol.replace(":USDT", "").replace("/", "")
            url = (
                "https://api.bitget.com/api/v2/mix/market/ticker"
                f"?symbol={raw}&productType=USDT-FUTURES"
            )
            r = requests.get(url, timeout=10).json()
            if r.get("code") == "00000" and r.get("data"):
                p = float(r["data"][0].get("lastPr", 0))
                return p if p > 0 else None
            logger.warning(f"[Trader] {self.symbol} price error: {r.get('msg')}")
            return None
        except Exception as e:
            logger.error(f"[Trader] {self.symbol} price fetch failed: {e}")
            return None

    # ----------------------------------------------------------
    # RSI CALCULATION for direction
    # ----------------------------------------------------------
    def _get_rsi(self):
        try:
            from bot.exchange_factory import fetch_ohlcv_direct
            import pandas as pd
            ohlcv = fetch_ohlcv_direct(self.symbol, "1m", limit=50)
            if not ohlcv or len(ohlcv) < 20:
                return 50  # Neutral default
            df = pd.DataFrame(
                ohlcv,
                columns=["ts","open","high","low","close","volume"]
            )
            close = df["close"].astype(float)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            return round(rsi, 1)
        except Exception as e:
            logger.error(f"[Trader] RSI error: {e}")
            return 50

    # ----------------------------------------------------------
    # POSITION SIZE
    # ----------------------------------------------------------
    def _calc_qty(self, price):
        try:
            from bot.exchange_factory import get_balance
            bal = get_balance(self.config)
            free = float(bal.get("free", 0))
            risk_pct = float(self.config.get("BOT_RISK_PCT", "15.0"))
            max_usd = float(self.config.get("BOT_MAX_POS_USD", "4.0"))
            risk_usd = min(free * risk_pct / 100, max_usd)
            if risk_usd < 6.0:
                risk_usd = 6.0
            qty = math.ceil((risk_usd / price) * 1000) / 1000
            logger.info(
                f"[Trader] {self.symbol} | Free:{free:.2f} "
                f"Risk:${risk_usd:.2f} Qty:{qty}"
            )
            return qty
        except Exception as e:
            logger.error(f"[Trader] qty error: {e}")
            return 0

    # ----------------------------------------------------------
    # ORDER EXECUTION
    # ----------------------------------------------------------
    def _execute(self, direction, price):
        qty = self._calc_qty(price)
        if not qty or qty <= 0:
            return False
        try:
            from bot.exchange_factory import place_order_direct, place_tpsl_direct
            order = place_order_direct(self.config, self.symbol, direction, qty)
            if order:
                self.last_trade_time = time.time()
                logger.info(
                    f"[Trader] {self.symbol} ✅ {direction.upper()} "
                    f"{qty} @ {price}"
                )
                # Auto TP/SL
                tp = float(self.config.get("BOT_TP_PCT", "3.0")) / 100
                sl = float(self.config.get("BOT_SL_PCT", "1.5")) / 100
                place_tpsl_direct(
                    self.config, self.symbol, direction, price, tp, sl
                )
                return True
            logger.error(f"[Trader] {self.symbol} ❌ Order failed")
            return False
        except Exception as e:
            logger.error(f"[Trader] execute error: {e}")
            return False

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

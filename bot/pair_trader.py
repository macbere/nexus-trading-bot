"""NEXUS Pair Trader - Production Version"""
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
        self.cooldown_secs = float(config.get("BOT_TRADE_COOLDOWN_MIN", 10)) * 60

    def _get_price(self):
        try:
            raw = self.symbol.replace("/USDT:USDT","USDT").replace("/","").upper()
            url = (f"https://api.bitget.com/api/v2/mix/market/ticker"
                   f"?symbol={raw}&productType=USDT-FUTURES")
            r = requests.get(url, timeout=10).json()
            if r.get("code") == "00000" and r.get("data"):
                p = float(r["data"][0].get("lastPr", 0))
                return p if p > 0 else None
            return None
        except Exception as e:
            logger.error(f"[Trader] Price error {self.symbol}: {e}")
            return None

    def _get_rsi(self):
        try:
            from bot.exchange_factory import fetch_ohlcv_direct
            import pandas as pd
            ohlcv = fetch_ohlcv_direct(self.symbol, "1m", limit=50)
            if not ohlcv or len(ohlcv) < 20:
                return 50
            df = pd.DataFrame(ohlcv, columns=["ts","o","h","l","c","v"])
            close = df["c"].astype(float)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            return float((100 - (100 / (1 + rs))).iloc[-1])
        except Exception:
            return 50

    def _calc_qty(self, price):
        try:
            from bot.exchange_factory import get_balance, _get_min_qty
            bal = get_balance(self.config)
            free = float(bal.get("free", 0))
            risk_pct = float(self.config.get("BOT_RISK_PCT", "15.0"))
            max_usd = float(self.config.get("BOT_MAX_POS_USD", "4.0"))
            risk_usd = min(free * risk_pct / 100, max_usd)
            if risk_usd < 6.0:
                risk_usd = 6.0

            # Get minimum lot size for this symbol
            min_qty = _get_min_qty(self.symbol)
            min_notional = min_qty * price

            # If minimum order costs more than our risk budget, skip
            if min_notional > free * 0.8:
                logger.warning(
                    f"[Trader] {self.symbol} min order ${min_notional:.2f} "
                    f"exceeds balance ${free:.2f} - skipping"
                )
                return 0

            # Calculate qty and ensure it meets minimum
            raw_qty = risk_usd / price
            qty = max(raw_qty, min_qty)
            qty = math.ceil(qty / min_qty) * min_qty
            qty = round(qty, 6)

            logger.info(
                f"[Trader] {self.symbol} | Free:{free:.2f} "
                f"Risk:${risk_usd:.2f} MinQty:{min_qty} Qty:{qty}"
            )
            return qty
        except Exception as e:
            logger.error(f"[Trader] Qty error: {e}")
            return 0

    def trade_with_score(self, scanner_score, rsi=None):
        try:
            # Cooldown check
            elapsed = time.time() - self.last_trade_time
            if self.last_trade_time > 0 and elapsed < self.cooldown_secs:
                mins = int((self.cooldown_secs - elapsed) / 60)
                logger.info(f"[Trader] {self.symbol} cooldown {mins}m")
                return False

            score = float(scanner_score)
            logger.info(f"[Trader] {self.symbol} | Score:{score:.1f}")

            if score < self.min_score:
                logger.info(f"[Trader] {self.symbol} score {score:.1f} < threshold {self.min_score}, skip")
                return False

            price = self._get_price()
            if not price:
                return False

            if rsi is None:
                rsi = self._get_rsi()

            # Direction: RSI >= 65 = overbought = SHORT, else LONG
            direction = "sell" if rsi >= 65 else "buy"
            dir_label = "SHORT" if direction == "sell" else "LONG"

            logger.info(f"[Trader] {self.symbol} | RSI:{rsi:.1f} | {dir_label} @ {price} | Score:{score:.1f}")

            qty = self._calc_qty(price)
            if not qty or qty <= 0:
                logger.warning(f"[Trader] {self.symbol} qty=0, skip")
                return False

            from bot.exchange_factory import place_order_direct
            order = place_order_direct(self.config, self.symbol, direction, qty)

            if order:
                self.last_trade_time = time.time()
                logger.info(f"[Trader] {self.symbol} ✅ {dir_label} {qty} @ {price}")
                return True
            else:
                logger.error(f"[Trader] {self.symbol} ❌ Order failed")
                return False

        except Exception as e:
            import traceback
            logger.error(f"[Trader] {self.symbol} error: {e}")
            logger.error(traceback.format_exc())
            return False

    def trade(self):
        return self.trade_with_score(self.min_score + 1)

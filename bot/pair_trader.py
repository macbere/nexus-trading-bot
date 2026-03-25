"""Pair Trader - Complete unified trading execution"""
import time
import logging
import requests
import math

logger = logging.getLogger(__name__)


class PairTrader:
    """Executes trades for a single trading pair using scanner scores"""

    def __init__(self, symbol, config, exchange):
        self.symbol = symbol
        self.config = config
        self.exchange = config
        self.last_trade_time = 0
        self.min_trade_score = float(config.get("MIN_TRADE_SCORE", 20))
        cooldown_min = float(config.get("BOT_TRADE_COOLDOWN_MIN", 10))
        self.cooldown_seconds = cooldown_min * 60

    def _symbol_to_bitget(self, symbol):
        """Convert BTC/USDT:USDT -> BTCUSDT"""
        return symbol.replace(":USDT", "").replace("/", "")

    def _get_price(self):
        """Fetch current price via direct Bitget REST API"""
        try:
            raw = self._symbol_to_bitget(self.symbol)
            url = (
                f"https://api.bitget.com/api/v2/mix/market/ticker"
                f"?symbol={raw}&productType=USDT-FUTURES"
            )
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("code") != "00000" or not data.get("data"):
                logger.warning(
                    f"[PairTrader] {self.symbol} price fetch failed: "
                    f"{data.get('msg')}"
                )
                return None
            price = float(data["data"][0].get("lastPr", 0))
            if not price:
                return None
            return price
        except Exception as e:
            logger.error(f"[PairTrader] {self.symbol} price error: {e}")
            return None

    def _calc_qty(self, price):
        """Calculate position size based on balance and risk settings"""
        try:
            from bot.exchange_factory import get_balance
            bal = get_balance(self.config)
            balance = float(bal.get("free", 0))
            risk_pct = float(self.config.get("BOT_RISK_PCT", "15.0"))
            max_pos_usd = float(self.config.get("BOT_MAX_POS_USD", "4.0"))
            risk_usd = min(balance * (risk_pct / 100), max_pos_usd)

            # Enforce Bitget minimum $5 notional with buffer
            min_notional = 6.0
            if risk_usd < min_notional:
                logger.warning(
                    f"[PairTrader] Risk ${risk_usd:.4f} below minimum "
                    f"${min_notional}, using minimum"
                )
                risk_usd = min_notional

            qty = risk_usd / price if price > 0 else 0
            qty = math.ceil(qty * 100) / 100  # Always round up

            logger.info(
                f"[PairTrader] Balance:{balance:.4f} USDT | "
                f"Risk:${risk_usd:.4f} | Qty:{qty:.4f}"
            )
            return qty
        except Exception as e:
            logger.error(f"[PairTrader] Qty calc error: {e}")
            return 0

    def _place_order(self, direction, qty, current_price):
        """Place order and immediately set TP/SL"""
        try:
            from bot.exchange_factory import place_order_direct, place_tpsl_direct
            order = place_order_direct(
                self.config, self.symbol, direction, qty
            )

            if order:
                self.last_trade_time = time.time()
                logger.info(
                    f"[PairTrader] {self.symbol} ✅ ORDER SUCCESS | "
                    f"Dir:{direction} Qty:{qty} @ {current_price}"
                )
                # Auto TP/SL immediately
                try:
                    tp_pct = float(
                        self.config.get("BOT_TP_PCT", "3.0")
                    ) / 100
                    sl_pct = float(
                        self.config.get("BOT_SL_PCT", "1.5")
                    ) / 100
                    place_tpsl_direct(
                        self.config, self.symbol, direction,
                        current_price, tp_pct, sl_pct
                    )
                except Exception as tpsl_err:
                    logger.error(
                        f"[PairTrader] TP/SL error: {tpsl_err}"
                    )
                return True
            else:
                logger.error(f"[PairTrader] {self.symbol} ❌ ORDER FAILED")
                return False
        except Exception as e:
            logger.error(f"[PairTrader] Order error: {e}")
            return False

    def trade_with_score(self, scanner_score):
        """
        Main entry point - uses scanner score directly.
        Called by PairEngine with pre-computed score.
        """
        try:
            # Cooldown check
            elapsed = time.time() - self.last_trade_time
            if self.last_trade_time > 0 and elapsed < self.cooldown_seconds:
                remaining = int((self.cooldown_seconds - elapsed) / 60)
                logger.info(
                    f"[PairTrader] {self.symbol} in cooldown "
                    f"({remaining}m remaining)"
                )
                return False

            score = scanner_score
            logger.info(
                f"[PairTrader] {self.symbol} | Scanner Score: {score:.1f}"
            )

            if score < self.min_trade_score:
                logger.info(
                    f"[PairTrader] {self.symbol} score {score:.1f} "
                    f"below threshold {self.min_trade_score}, skipping"
                )
                return False

            # Get current price
            current_price = self._get_price()
            if not current_price:
                return False

            logger.info(
                f"[PairTrader] {self.symbol} | Price:{current_price} | "
                f"Score:{score:.1f} -> Executing LONG"
            )

            # Calculate position size
            qty = self._calc_qty(current_price)
            if not qty or qty <= 0:
                logger.warning(
                    f"[PairTrader] {self.symbol} qty=0, skipping"
                )
                return False

            # Execute trade
            return self._place_order("buy", qty, current_price)

        except Exception as e:
            import traceback
            logger.error(f"[PairTrader] {self.symbol} error: {e}")
            logger.error(traceback.format_exc())
            return False

    def trade(self):
        """Legacy fallback - redirects to trade_with_score"""
        return self.trade_with_score(self.min_trade_score + 1)

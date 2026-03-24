"""Pair Trader - Direct REST API order execution"""
import time
import logging

logger = logging.getLogger(__name__)


class PairTrader:
    """Executes trades for a single trading pair"""

    def __init__(self, symbol, config, exchange):
        self.symbol = symbol
        self.config = config
        # exchange is now the config dict from build_exchange()
        self.exchange = config
        self.last_trade_time = 0
        self.min_trade_score = float(config.get("MIN_TRADE_SCORE", 45))
        cooldown_min = float(config.get("BOT_TRADE_COOLDOWN_MIN", 30))
        self.cooldown_seconds = cooldown_min * 60

    def trade(self):
        """Main trade execution method"""
        try:
            # Cooldown check
            elapsed = time.time() - self.last_trade_time
            if self.last_trade_time > 0 and elapsed < self.cooldown_seconds:
                remaining = int((self.cooldown_seconds - elapsed) / 60)
                logger.info(f"[PairTrader] {self.symbol} in cooldown ({remaining}m remaining)")
                return False

            # Multi-timeframe analysis
            from bot.multi_timeframe import MultiTimeframeAnalyzer
            mtf = MultiTimeframeAnalyzer(self.config, self.config)
            result = mtf.analyze_all_timeframes(self.symbol)

            score = result.get("score", 50) if result else 50
            signal = result.get("signal", "NEUTRAL") if result else "NEUTRAL"

            logger.info(f"[PairTrader] {self.symbol} - Score: {score:.1f}, Signal: {signal}")

            if score < self.min_trade_score:
                logger.info(
                    f"[PairTrader] {self.symbol} - Score {score:.1f} "
                    f"below threshold {self.min_trade_score}"
                )
                return False

            # Determine direction
            if signal in ["STRONG_BUY", "BUY"]:
                direction = "buy"
            elif signal in ["STRONG_SELL", "SELL"]:
                direction = "sell"
            elif score >= self.min_trade_score:
                direction = "buy"
                logger.info(
                    f"[PairTrader] {self.symbol} - Neutral but score OK, defaulting LONG"
                )
            else:
                logger.info(f"[PairTrader] {self.symbol} - Neutral signal, skipping")
                return False

            # Fetch current price via direct API
            current_price = self._get_price()
            if not current_price:
                return False

            # Calculate position size
            qty = self._calc_qty(current_price)
            if not qty or qty <= 0:
                logger.warning(f"[PairTrader] {self.symbol} qty=0, skipping trade")
                return False

            logger.info(
                f"[PairTrader] {self.symbol} --- "
                f"{'LONG' if direction == 'buy' else 'SHORT'} {qty} @ {current_price}"
            )

            # Place order via direct REST API
            from bot.exchange_factory import place_order_direct
            order = place_order_direct(self.config, self.symbol, direction, qty)

            if order:
                self.last_trade_time = time.time()
                logger.info(
                    f"[PairTrader] {self.symbol} ✅ ORDER SUCCESS - Score: {score:.1f}"
                )
                return True
            else:
                logger.error(f"[PairTrader] {self.symbol} ❌ ORDER FAILED")
                return False

        except Exception as e:
            import traceback
            logger.error(f"[PairTrader] {self.symbol} trade error: {e}")
            logger.error(traceback.format_exc())
            return False

    def _get_price(self):
        """Fetch current price via direct Bitget REST API"""
        try:
            import requests
            raw = self.symbol.replace("/USDT:USDT", "USDT").replace("/", "")
            url = (
                f"https://api.bitget.com/api/v2/mix/market/ticker"
                f"?symbol={raw}&productType=USDT-FUTURES"
            )
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("code") != "00000" or not data.get("data"):
                logger.warning(f"[PairTrader] {self.symbol} price fetch failed: {data.get('msg')}")
                return None
            price = float(data["data"][0].get("lastPr", 0))
            if not price:
                logger.warning(f"[PairTrader] {self.symbol} price=0, skipping")
                return None
            logger.info(f"[PairTrader] {self.symbol} price: {price}")
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
            risk_pct = float(self.config.get("BOT_RISK_PCT", "5.0"))
            max_pos_usd = float(self.config.get("BOT_MAX_POS_USD", "3.0"))
            risk_usd = min(balance * (risk_pct / 100), max_pos_usd)
            qty = risk_usd / price if price > 0 else 0
            logger.info(
                f"[PairTrader] Balance: {balance:.4f} USDT | "
                f"Risk: ${risk_usd:.4f} | Qty: {qty:.4f}"
            )
            return round(qty, 2)
        except Exception as e:
            logger.error(f"[PairTrader] Error calculating qty: {e}")
            return 0
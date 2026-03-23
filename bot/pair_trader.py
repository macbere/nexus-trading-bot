"""Pair Trader - executes trades"""
import time
import logging

logger = logging.getLogger(__name__)

class PairTrader:
    def __init__(self, symbol, config, exchange, mtf_analyzer=None):
        self.symbol = symbol
        self.config = config
        self.exchange = exchange
        self.last_trade_time = 0
        self.min_trade_score = float(config.get("MIN_TRADE_SCORE", "45"))
        self.cooldown_minutes = int(config.get("BOT_TRADE_COOLDOWN_MIN", "30"))

    def trade(self):
        try:
            now = time.time()
            if now - self.last_trade_time < self.cooldown_minutes * 60:
                return False

            from bot.multi_timeframe import MultiTimeframeAnalyzer
            mtf = MultiTimeframeAnalyzer(self.exchange, self.config)
            result = mtf.analyze_all_timeframes(self.symbol)

            score = result.get("score", 50) if result else 50
            signal = result.get("signal", "NEUTRAL") if result else "NEUTRAL"

            logger.info(f"[PairTrader] {self.symbol} - Score: {score:.1f}, Signal: {signal}")

            if score < self.min_trade_score:
                logger.info(f"[PairTrader] {self.symbol} - Score {score:.1f} below threshold {self.min_trade_score}")
                return False

            if signal in ["STRONG_BUY", "BUY"]:
                direction = "LONG"
            elif signal in ["STRONG_SELL", "SELL"]:
                direction = "SHORT"
            elif score >= self.min_trade_score:
                direction = "LONG"
                logger.info(f"[PairTrader] {self.symbol} - Neutral but score OK, defaulting LONG")
            else:
                logger.info(f"[PairTrader] {self.symbol} - Neutral signal, skipping")
                return False

            # Validate symbol and fetch ticker safely
            markets = self.exchange.markets
            if self.symbol not in markets:
                logger.warning(f"[PairTrader] {self.symbol} not in markets, skipping")
                return False
            try:
                ticker = self.exchange.fetch_ticker(self.symbol)
                if not ticker or "last" not in ticker or not ticker["last"]:
                    logger.warning(f"[PairTrader] {self.symbol} invalid ticker data, skipping")
                    return False
                current_price = ticker["last"]
            except Exception as te:
                logger.warning(f"[PairTrader] {self.symbol} fetch_ticker failed: {te}, skipping")
                return False

            qty = self._calc_qty(current_price)
            if not qty or qty <= 0:
                logger.warning(f"[PairTrader] {self.symbol} qty=0, skipping trade")
                return False

            if direction == "LONG":
                tp_price = round(current_price * 1.025, 6)
                sl_price = round(current_price * 0.985, 6)
            else:
                tp_price = round(current_price * 0.975, 6)
                sl_price = round(current_price * 1.015, 6)

            logger.info(f"[PairTrader] {self.symbol} --- {direction} {qty} @ {current_price}")
            logger.info(f"[PairTrader] {self.symbol} TP: {tp_price}, SL: {sl_price}")

            order = self.exchange.create_market_order(self.symbol, direction.lower(), qty)

            if order:
                self.last_trade_time = time.time()
                logger.info(f"[PairTrader] {self.symbol} ORDER SUCCESS - Score: {score:.1f}")
                return True
            else:
                logger.error(f"[PairTrader] {self.symbol} ORDER FAILED")
                return False

        except Exception as e:
            import traceback
            logger.error(f"[PairTrader] {self.symbol} trade error: {e}")
            logger.error(traceback.format_exc())
            return False

    def _calc_qty(self, price):
        try:
            bal = self.exchange.fetch_balance({"type": "swap"})
            balance = float(bal.get("USDT", {}).get("free", 0) or 0)
            risk_pct = float(self.config.get("BOT_RISK_PCT", "10.0"))
            max_pos_usd = float(self.config.get("BOT_MAX_POS_USD", "3.0"))
            risk_usd = min(balance * (risk_pct / 100), max_pos_usd)
            qty = risk_usd / price if price > 0 else 0
            logger.info(f"[PairTrader] Balance: {balance:.4f} USDT, risk_usd: {risk_usd:.4f}, qty: {qty:.4f}")
            return round(qty, 2)
        except Exception as e:
            logger.error(f"[PairTrader] Error calculating qty: {e}")
            return 0

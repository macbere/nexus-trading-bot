"""Strategy Module - EMA/RSI signals using direct REST API"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class HFScalperStrategy:
    """EMA crossover + RSI strategy using direct Bitget API"""

    def __init__(self, config, exchange=None):
        self.config = config
        self.ema_fast = int(config.get("BOT_EMA_FAST", 9))
        self.ema_slow = int(config.get("BOT_EMA_SLOW", 21))
        self.rsi_ob = float(config.get("BOT_RSI_OB", 60))
        self.rsi_os = float(config.get("BOT_RSI_OS", 40))
        self.rsi_period = int(config.get("BOT_RSI_PERIOD", 14))

    def get_signal(self, symbol, timeframe="1m"):
        try:
            from bot.exchange_factory import fetch_ohlcv_direct
            ohlcv = fetch_ohlcv_direct(symbol, timeframe, limit=100)
            if not ohlcv or len(ohlcv) < 30:
                return "FLAT"

            df = pd.DataFrame(
                ohlcv,
                columns=["ts", "open", "high", "low", "close", "volume"]
            )
            df["close"] = df["close"].astype(float)

            df["ema_fast"] = df["close"].ewm(span=self.ema_fast, adjust=False).mean()
            df["ema_slow"] = df["close"].ewm(span=self.ema_slow, adjust=False).mean()

            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
            rs = gain / loss
            df["rsi"] = 100 - (100 / (1 + rs))

            last = df.iloc[-1]
            ema_cross_up = last["ema_fast"] > last["ema_slow"]
            ema_cross_dn = last["ema_fast"] < last["ema_slow"]
            rsi = last["rsi"]

            if ema_cross_up and rsi < self.rsi_ob:
                return "LONG"
            elif ema_cross_dn and rsi > self.rsi_os:
                return "SHORT"
            return "FLAT"

        except Exception as e:
            logger.error(f"[Strategy] Signal error for {symbol}: {e}")
            return "FLAT"

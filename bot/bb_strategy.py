import logging
import pandas as pd
from dataclasses import dataclass
from ta.volatility import BollingerBands
from ta.momentum  import RSIIndicator

logger = logging.getLogger(__name__)

@dataclass
class BBSignal:
    direction: str
    price:     float
    rsi:       float
    bb_upper:  float
    bb_lower:  float
    bb_mid:    float
    pct_b:     float   # 0=at lower band, 1=at upper band
    strategy:  str = "BB"

class BollingerStrategy:
    def __init__(self, config):
        self.symbol     = config.get("BOT_SYMBOL",     "DOGE/USDT:USDT")
        self.timeframe  = config.get("BOT_TIMEFRAME",  "1m")
        self.bb_period  = int(config.get("BOT_BB_PERIOD", "20"))
        self.bb_std     = float(config.get("BOT_BB_STD",  "2.0"))
        self.rsi_period = int(config.get("BOT_RSI_PERIOD","14"))
        self.rsi_ob     = float(config.get("BOT_RSI_OB",  "60"))
        self.rsi_os     = float(config.get("BOT_RSI_OS",  "40"))
        logger.info(f"[BB] Ready | period={self.bb_period} std={self.bb_std}")

    def _fetch_candles(self, exchange):
        from bot.exchange_factory import fetch_ohlcv_direct
        ohlcv = fetch_ohlcv_direct(self.symbol, self.timeframe, limit=100)
        df    = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
        df["close"] = df["close"].astype(float)
        df["close"] = df["close"].replace(0, float("nan")).ffill()
        return df

    def generate_signal(self, exchange) -> BBSignal:
        df    = self._fetch_candles(exchange)
        close = df["close"]
        price = float(close.iloc[-1])

        # Bollinger Bands
        bb     = BollingerBands(close, window=self.bb_period, window_dev=self.bb_std)
        upper  = float(bb.bollinger_hband().iloc[-1])
        lower  = float(bb.bollinger_lband().iloc[-1])
        mid    = float(bb.bollinger_mavg().iloc[-1])
        pct_b  = (price - lower) / (upper - lower) if (upper - lower) > 0 else 0.5

        # RSI confirmation
        rsi = float(RSIIndicator(close, window=self.rsi_period).rsi().iloc[-1])

        # Signal logic
        # LONG: price touches/below lower band + RSI oversold
        if price <= lower * 1.005 and rsi < self.rsi_ob:
            direction = "LONG"
        # SHORT: price touches/above upper band + RSI overbought
        elif price >= upper * 0.995 and rsi > self.rsi_os:
            direction = "SHORT"
        else:
            direction = "FLAT"

        sig = BBSignal(
            direction = direction,
            price     = price,
            rsi       = round(rsi, 2),
            bb_upper  = round(upper, 5),
            bb_lower  = round(lower, 5),
            bb_mid    = round(mid,   5),
            pct_b     = round(pct_b, 3),
            strategy  = "BB"
        )
        logger.info(
            f"[BB] Signal={direction} price={price:.4f} "
            f"BB=[{lower:.4f}-{upper:.4f}] pct_b={pct_b:.2f} RSI={rsi:.2f}"
        )
        return sig

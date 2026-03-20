from bot.exchange_factory import fetch_ohlcv_direct
import logging
import pandas as pd
from ta.trend    import EMAIndicator, ADXIndicator
from ta.momentum import RSIIndicator

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """
    Detects whether market is TRENDING or RANGING.
    TRENDING  → use EMA/RSI strategy
    RANGING   → use Bollinger Bands strategy
    """
    def __init__(self, config):
        self.symbol    = config.get("BOT_SYMBOL",    "DOGE/USDT:USDT")
        self.timeframe = config.get("BOT_TIMEFRAME", "1m")
        self.adx_period    = 14
        self.adx_threshold = 25   # ADX > 25 = trending, < 25 = ranging

    def _fetch_candles(self, exchange, limit=50):
        ohlcv = fetch_ohlcv_direct(self.symbol, self.timeframe, limit=limit)
        df    = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
        for col in ["open","high","low","close","volume"]:
            df[col] = df[col].astype(float)
        return df

    def get_condition(self, exchange):
        """Returns: TRENDING or RANGING"""
        try:
            df = self._fetch_candles(exchange)

            # ADX measures trend strength
            adx_val = float(
                ADXIndicator(df["high"], df["low"], df["close"],
                             window=self.adx_period).adx().iloc[-1]
            )

            # EMA spread — wide spread = trending
            ema9  = float(EMAIndicator(df["close"], window=9).ema_indicator().iloc[-1])
            ema21 = float(EMAIndicator(df["close"], window=21).ema_indicator().iloc[-1])
            ema_spread_pct = abs(ema9 - ema21) / ema21 * 100

            # BB bandwidth — low bandwidth = ranging (squeeze)
            bb_high = df["close"].rolling(20).mean() + 2 * df["close"].rolling(20).std()
            bb_low  = df["close"].rolling(20).mean() - 2 * df["close"].rolling(20).std()
            bb_bw   = float(((bb_high - bb_low) / df["close"].rolling(20).mean()).iloc[-1])

            if adx_val > self.adx_threshold or ema_spread_pct > 0.15:
                condition = "TRENDING"
            else:
                condition = "RANGING"

            logger.info(
                f"[Market] ADX={adx_val:.1f} EMA_spread={ema_spread_pct:.3f}% "
                f"BB_bw={bb_bw:.4f} → {condition}"
            )
            return condition, adx_val, ema_spread_pct

        except Exception as e:
            logger.warning(f"[Market] Analysis error: {e} — defaulting TRENDING")
            return "TRENDING", 0, 0


class MultiStrategy:
    """
    Runs both strategies, picks the right one based on market conditions.
    """
    def __init__(self, config, ema_strategy, bb_strategy):
        self.config       = config
        self.ema          = ema_strategy
        self.bb           = bb_strategy
        self.analyzer     = MarketAnalyzer(config)
        self.symbol       = config.get("BOT_SYMBOL", "DOGE/USDT:USDT")
        self.last_condition = "TRENDING"
        self.condition_counts = {"TRENDING": 0, "RANGING": 0}
        logger.info("[MultiStrategy] Ready — EMA/RSI + Bollinger Bands active")

    def generate_signal(self, exchange):
        # Analyze market every tick
        condition, adx, spread = self.analyzer.get_condition(exchange)
        self.last_condition = condition
        self.condition_counts[condition] += 1

        if condition == "TRENDING":
            logger.info(f"[MultiStrategy] TRENDING market → using EMA/RSI strategy")
            sig = self.ema.generate_signal(exchange)
            sig.strategy = "EMA_RSI"
            return sig
        else:
            logger.info(f"[MultiStrategy] RANGING market → using Bollinger Bands strategy")
            sig = self.bb.generate_signal(exchange)
            # Normalize BBSignal to match what bot_engine expects
            sig.direction = sig.direction
            return sig

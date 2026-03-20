from bot.exchange_factory import fetch_ohlcv_direct
"""
strategy.py  —  HFT Scalper Strategy
────────────────────────────────────────────────────────────
Uses the lightweight `ta` library (~2 MB) instead of pandas_ta
to stay within PythonAnywhere Free Tier disk limits.

Indicators: EMA fast/slow, RSI, VWAP
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import ta
import ccxt

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    direction:  str
    symbol:     str
    price:      float
    timestamp:  float           = field(default_factory=time.time)
    ema_fast:   Optional[float] = None
    ema_slow:   Optional[float] = None
    rsi:        Optional[float] = None
    vwap:       Optional[float] = None


class HFScalperStrategy:

    def __init__(self, cfg: dict):
        self.symbol         = cfg.get("BOT_SYMBOL",          "BTC/USDT:USDT")
        self.timeframe      = cfg.get("BOT_TIMEFRAME",        "1m")
        self.ema_fast       = int(cfg.get("BOT_EMA_FAST",     9))
        self.ema_slow       = int(cfg.get("BOT_EMA_SLOW",     21))
        self.rsi_period     = int(cfg.get("BOT_RSI_PERIOD",   14))
        self.rsi_overbought = float(cfg.get("BOT_RSI_OB",     65.0))
        self.rsi_oversold   = float(cfg.get("BOT_RSI_OS",     35.0))
        self.candle_limit   = int(cfg.get("BOT_CANDLE_LIMIT", 100))

    def _fetch_ohlcv(self, exchange: ccxt.Exchange) -> pd.DataFrame:
        raw = fetch_ohlcv_direct(
                self.symbol,
                self.timeframe,
                limit=self.candle_limit
            )
        df = pd.DataFrame(raw, columns=["ts","open","high","low","close","volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        df.set_index("ts", inplace=True)
        for col in ["open","high","low","close","volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df["ema_fast"] = ta.trend.EMAIndicator(close=df["close"], window=self.ema_fast).ema_indicator()
        df["ema_slow"] = ta.trend.EMAIndicator(close=df["close"], window=self.ema_slow).ema_indicator()
        df["rsi"]      = ta.momentum.RSIIndicator(close=df["close"], window=self.rsi_period).rsi()
        try:
            df["vwap"] = ta.volume.VolumeWeightedAveragePrice(
                high=df["high"], low=df["low"], close=df["close"], volume=df["volume"], window=14
            ).volume_weighted_average_price()
        except Exception:
            tp = (df["high"] + df["low"] + df["close"]) / 3
            df["vwap"] = (tp * df["volume"]).cumsum() / df["volume"].cumsum()
        return df

    def generate_signal(self, exchange: ccxt.Exchange) -> Signal:
        try:
            df = self._fetch_ohlcv(exchange)
            df = self._compute_indicators(df)
        except ccxt.NetworkError as exc:
            logger.warning("[Strategy] Network error: %s", exc)
            return Signal(direction="flat", symbol=self.symbol, price=0.0)
        except Exception as exc:
            logger.error("[Strategy] Error: %s", exc)
            return Signal(direction="flat", symbol=self.symbol, price=0.0)

        last    = df.iloc[-1]
        ema_f   = last["ema_fast"]
        ema_s   = last["ema_slow"]
        rsi_val = last["rsi"]
        vwap_v  = last["vwap"]
        price   = last["close"]

        if pd.isna(ema_f) or pd.isna(ema_s) or pd.isna(rsi_val):
            return Signal(direction="flat", symbol=self.symbol, price=price)

        vwap_ok    = pd.notna(vwap_v)
        long_cond  = ema_f >= ema_s * 0.999 and rsi_val < self.rsi_overbought and (not vwap_ok or price > vwap_v)
        short_cond = ema_f <= ema_s * 1.001 and rsi_val > self.rsi_oversold  and (not vwap_ok or price < vwap_v)
        direction  = "long" if long_cond else ("short" if short_cond else "flat")

        sig = Signal(
            direction=direction, symbol=self.symbol, price=price,
            ema_fast=round(float(ema_f),4), ema_slow=round(float(ema_s),4),
            rsi=round(float(rsi_val),2),
            vwap=round(float(vwap_v),4) if vwap_ok else None,
        )
        logger.info("[Strategy] Signal → %-5s | price=%.4f | RSI=%.2f | EMA_F=%.4f | EMA_S=%.4f",
                    sig.direction.upper(), sig.price, sig.rsi, sig.ema_fast, sig.ema_slow)
        return sig

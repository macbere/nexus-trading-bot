"""
Position Monitor - Smart Exit System
Runs every 5 minutes. Closes positions that have reached profit target
or are losing AND signal has reversed.
NEVER closes winning positions prematurely.
"""
import time
import json
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class PositionMonitor:
    def __init__(self, config):
        self.config = config
        self.running = False
        self.thread = None
        self.position_open_times = {}

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("[Monitor] Smart position monitor started")

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                self._check_and_manage()
            except Exception as e:
                logger.error(f"[Monitor] Error: {e}")
            time.sleep(300)  # Check every 5 minutes

    def _get_rsi(self, symbol):
        try:
            from bot.exchange_factory import fetch_ohlcv_direct
            import pandas as pd
            ohlcv = fetch_ohlcv_direct(symbol, "1m", limit=30)
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

    def _check_and_manage(self):
        from bot.exchange_factory import get_positions, close_position_direct
        positions = get_positions(self.config)

        if not positions:
            return

        logger.info(f"[Monitor] Checking {len(positions)} positions...")

        for p in positions:
            try:
                symbol   = p.get("symbol", "")
                hold     = p.get("holdSide", "long").lower()
                size     = float(p.get("total", 0))
                entry    = float(p.get("openPriceAvg", 0))
                mark     = float(p.get("markPrice", 0))
                pnl      = float(p.get("unrealizedPL", 0))
                margin   = float(p.get("margin", 1))

                if size <= 0 or entry <= 0 or margin <= 0:
                    continue

                roe = (pnl / margin) * 100

                # Track when position opened
                if symbol not in self.position_open_times:
                    self.position_open_times[symbol] = time.time()

                hours_open = (time.time() - self.position_open_times[symbol]) / 3600

                # Convert symbol for RSI check
                base = symbol.replace("USDT","")
                sym_ccxt = f"{base}/USDT:USDT"

                logger.info(
                    f"[Monitor] {symbol} | {hold.upper()} | "
                    f"ROE:{roe:+.2f}% | Open:{hours_open:.1f}h"
                )

                # RULE 1: Take profit at +5% ROE
                if roe >= 5.0:
                    logger.info(f"[Monitor] 🎯 {symbol} hit +5% ROE - taking profit!")
                    if close_position_direct(self.config, sym_ccxt, hold, size):
                        del self.position_open_times[symbol]
                    continue

                # RULE 2: Cut loss if open > 3 hours AND ROE < -3% AND signal reversed
                if hours_open >= 3.0 and roe <= -3.0:
                    rsi = self._get_rsi(sym_ccxt)
                    signal_reversed = (
                        (hold == "long"  and rsi > 60) or
                        (hold == "short" and rsi < 40)
                    )
                    if signal_reversed:
                        logger.info(
                            f"[Monitor] ✂️ {symbol} cutting loss: "
                            f"ROE:{roe:.2f}% open:{hours_open:.1f}h RSI:{rsi:.1f}"
                        )
                        if close_position_direct(self.config, sym_ccxt, hold, size):
                            del self.position_open_times[symbol]
                    else:
                        logger.info(
                            f"[Monitor] ⏳ {symbol} holding: signal not reversed RSI:{rsi:.1f}"
                        )
                    continue

                logger.info(f"[Monitor] ✋ {symbol} holding - conditions not met")

            except Exception as e:
                logger.error(f"[Monitor] Position check error: {e}")

    def log_trade(self, *args, **kwargs):
        pass  # Placeholder for compatibility

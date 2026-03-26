"""Market Scanner - High Quality Signals Only"""
import requests
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)

BLACKLIST = ["LUNA/USDT:USDT", "UST/USDT:USDT"]


class MarketScanner:
    def __init__(self, config, exchange=None):
        self.config = config
        self.max_pairs = 3
        self.last_scan_time = 0
        self.top_pairs = []
        self.scores = {}
        logger.info("[Scanner] Ready - High Quality Signal Mode")

    def _get_top_pairs_by_volume(self, limit=30):
        try:
            url = "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES"
            resp = requests.get(url, timeout=10).json()
            if resp.get("code") == "00000":
                tickers = resp.get("data", [])
                tickers.sort(key=lambda x: float(x.get("usdtVol24h", 0)), reverse=True)
                pairs = []
                for t in tickers[:limit]:
                    symbol = t.get("symbol", "")
                    if symbol and symbol.endswith("USDT"):
                        base = symbol.replace("USDT", "")
                        pair = f"{base}/USDT:USDT"
                        if pair not in BLACKLIST:
                            pairs.append(pair)
                return pairs
        except Exception as e:
            logger.error(f"[Scanner] Volume fetch error: {e}")
        return ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT",
                "XRP/USDT:USDT", "DOGE/USDT:USDT", "BNB/USDT:USDT"]

    def score_pair(self, symbol):
        """
        Score pair 0-100. Only high scores (>25) are traded.
        Requires EXTREME RSI + Volume surge for quality signals.
        """
        try:
            from bot.exchange_factory import fetch_ohlcv_direct
            ohlcv = fetch_ohlcv_direct(symbol, "1m", limit=60)
            if not ohlcv or len(ohlcv) < 30:
                return None

            df = pd.DataFrame(
                ohlcv,
                columns=["ts","open","high","low","close","volume"]
            )
            for col in ["open","high","low","close","volume"]:
                df[col] = df[col].astype(float)

            close  = df["close"]
            volume = df["volume"]
            price  = float(close.iloc[-1])

            if price <= 0:
                return None

            # USD volume filter - minimum $10,000
            usd_vol_now = float(volume.iloc[-1]) * price
            usd_vol_avg = float(volume.tail(20).mean()) * price
            if usd_vol_now < 10000:
                return None

            # RSI calculation
            delta = close.diff()
            gain  = delta.where(delta > 0, 0).rolling(14).mean()
            loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs    = gain / loss
            rsi   = float((100 - (100 / (1 + rs))).iloc[-1])

            # SCORE COMPONENTS
            # 1. RSI extremity (0-50 points) - MOST IMPORTANT
            # RSI below 25 or above 75 = very strong signal
            if rsi <= 20 or rsi >= 80:
                rsi_score = 50
            elif rsi <= 25 or rsi >= 75:
                rsi_score = 40
            elif rsi <= 30 or rsi >= 70:
                rsi_score = 30
            elif rsi <= 35 or rsi >= 65:
                rsi_score = 15
            else:
                rsi_score = 0  # RSI 35-65 = no signal

            # 2. Volume surge (0-30 points)
            vol_ratio = usd_vol_now / usd_vol_avg if usd_vol_avg > 0 else 1
            vol_score = min(vol_ratio * 8, 30)

            # 3. Price momentum (0-20 points)
            price_10 = float(close.iloc[-10])
            momentum = abs(price - price_10) / price_10 if price_10 > 0 else 0
            mom_score = min(momentum * 500, 20)

            # EMA trend confirmation
            ema9  = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
            ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
            trend_aligned = (rsi < 50 and ema9 < ema21) or (rsi > 50 and ema9 > ema21)

            total = rsi_score + vol_score + mom_score
            if not trend_aligned:
                total *= 0.7  # Reduce score if trend not aligned

            result = {
                "symbol":    symbol,
                "score":     round(total, 1),
                "rsi":       round(rsi, 1),
                "vol_ratio": round(vol_ratio, 2),
                "usd_vol":   round(usd_vol_now, 0),
                "price":     round(price, 8),
                "direction": "SHORT" if rsi >= 65 else "LONG",
            }

            logger.info(
                f"[Scanner] {symbol} | Score:{result['score']:.1f} | "
                f"RSI:{rsi:.1f} | Vol:{vol_ratio:.1f}x | "
                f"${usd_vol_now:,.0f} | {result['direction']}"
            )
            return result

        except Exception as e:
            logger.error(f"[Scanner] Score error {symbol}: {e}")
            return None

    def scan_all_markets(self):
        logger.info("[Scanner] Starting quality scan...")
        start = time.time()
        try:
            pairs = self._get_top_pairs_by_volume(limit=25)
            scored = []
            for symbol in pairs:
                result = self.score_pair(symbol)
                if result and result["score"] >= 20:
                    scored.append(result)

            scored.sort(key=lambda x: x["score"], reverse=True)
            self.top_pairs = [item["symbol"] for item in scored[:self.max_pairs]]
            self.scores    = {item["symbol"]: item for item in scored}

            elapsed = time.time() - start
            logger.info(
                f"[Scanner] Found {len(self.top_pairs)} quality pairs: "
                f"{self.top_pairs} in {elapsed:.1f}s"
            )
            return self.top_pairs

        except Exception as e:
            logger.error(f"[Scanner] Scan error: {e}")
            return []

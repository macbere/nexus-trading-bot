"""Market Scanner - Finds best trading pairs using direct Bitget API"""
import requests
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)

BLACKLIST = ["LUNA/USDT:USDT", "UST/USDT:USDT"]


class MarketScanner:
    def __init__(self, config, exchange):
        self.config = config
        self.exchange = exchange
        self.max_pairs = 3
        self.last_scan_time = 0
        self.top_pairs = []
        self.scores = {}
        logger.info("[Scanner] Ready - will scan top 10 pairs by volume")

    def _get_top_pairs_by_volume(self, limit=20):
        """Get top pairs by 24h USD volume from Bitget API"""
        try:
            url = "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES"
            resp = requests.get(url, timeout=10)
            data = resp.json()

            if data.get("code") == "00000":
                tickers = data.get("data", [])
                # Sort by USD volume (usdtVol24h field)
                tickers.sort(
                    key=lambda x: float(x.get("usdtVol24h", 0)),
                    reverse=True
                )
                top_pairs = []
                for t in tickers[:limit]:
                    symbol = t.get("symbol", "")
                    if symbol and symbol.endswith("USDT"):
                        # Convert BTCUSDT -> BTC/USDT:USDT
                        base = symbol.replace("USDT", "")
                        pair = f"{base}/USDT:USDT"
                        if pair not in BLACKLIST:
                            top_pairs.append(pair)

                logger.info(f"[Scanner] Top {len(top_pairs)} pairs by volume: {top_pairs}")
                return top_pairs
        except Exception as e:
            logger.error(f"[Scanner] Error fetching top pairs: {e}")

        # Fallback to known liquid pairs
        return [
            "BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT",
            "XRP/USDT:USDT", "DOGE/USDT:USDT", "ADA/USDT:USDT",
            "AVAX/USDT:USDT", "LINK/USDT:USDT", "DOT/USDT:USDT",
            "BNB/USDT:USDT"
        ]

    def score_pair(self, symbol):
        """Score a trading pair 0-100 based on profit potential"""
        try:
            from bot.exchange_factory import fetch_ohlcv_direct
            ohlcv = fetch_ohlcv_direct(symbol, "1m", limit=60)
            if not ohlcv or len(ohlcv) < 30:
                return None

            df = pd.DataFrame(
                ohlcv,
                columns=["ts", "open", "high", "low", "close", "volume"]
            )
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            close = df["close"]
            volume = df["volume"]
            price = float(close.iloc[-1])

            if price <= 0:
                return None

            # USD volume check - convert coin volume to USD
            usd_volume_recent = float(volume.iloc[-1]) * price
            usd_volume_avg = float(volume.tail(10).mean()) * price

            # Minimum $5,000 USD volume in last candle
            if usd_volume_recent < 5000:
                return None

            # 1. VOLATILITY SCORE (0-40 points)
            price_10_ago = float(close.iloc[-10])
            if price_10_ago > 0:
                price_change_pct = abs(price - price_10_ago) / price_10_ago
            else:
                price_change_pct = 0
            volatility_score = min(price_change_pct * 1000, 40)

            # 2. VOLUME SURGE SCORE (0-30 points)
            if usd_volume_avg > 0:
                volume_ratio = usd_volume_recent / usd_volume_avg
            else:
                volume_ratio = 1
            volume_score = min(volume_ratio * 10, 30)

            # 3. TREND STRENGTH - Simple EMA diff (0-20 points)
            ema_fast = close.ewm(span=9, adjust=False).mean()
            ema_slow = close.ewm(span=21, adjust=False).mean()
            ema_diff_pct = abs(
                float(ema_fast.iloc[-1]) - float(ema_slow.iloc[-1])
            ) / float(ema_slow.iloc[-1]) if float(ema_slow.iloc[-1]) > 0 else 0
            trend_score = min(ema_diff_pct * 2000, 20)

            # 4. RSI MOMENTUM SCORE (0-10 points)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            rsi_distance = min(abs(rsi - 50), 30)
            rsi_score = rsi_distance / 30 * 10

            total_score = volatility_score + volume_score + trend_score + rsi_score

            result = {
                "symbol": symbol,
                "score": round(total_score, 1),
                "price": round(price, 8),
                "volatility_pct": round(price_change_pct * 100, 3),
                "vol_ratio": round(volume_ratio, 2),
                "usd_vol": round(usd_volume_recent, 0),
                "rsi": round(rsi, 1),
            }
            logger.info(
                f"[Scanner] {symbol} | Score:{total_score:.1f} | "
                f"RSI:{rsi:.1f} | VolRatio:{volume_ratio:.2f} | "
                f"USDVol:${usd_volume_recent:,.0f}"
            )
            return result

        except Exception as e:
            logger.error(f"[Scanner] Error scoring {symbol}: {e}")
            return None

    def scan_all_markets(self):
        """Scan top pairs by volume and score them"""
        logger.info("[Scanner] Starting LIMITED market scan (top 10 by volume)...")
        start = time.time()

        try:
            pairs = self._get_top_pairs_by_volume(limit=20)
            logger.info(f"[Scanner] Scanning ONLY {len(pairs)} top pairs by volume")

            scored = []
            for symbol in pairs:
                result = self.score_pair(symbol)
                if result:
                    scored.append(result)

            scored.sort(key=lambda x: x["score"], reverse=True)
            self.top_pairs = [item["symbol"] for item in scored[:self.max_pairs]]
            self.scores = {item["symbol"]: item for item in scored}
            self.last_scan_time = time.time()

            elapsed = time.time() - start
            logger.info(
                f"[Scanner] Found {len(self.top_pairs)} top pairs: "
                f"{self.top_pairs}"
            )
            logger.info(f"[Scanner] Scan completed in {elapsed:.2f}s")
            return self.top_pairs

        except Exception as e:
            logger.error(f"[Scanner] Scan error: {e}")
            return []

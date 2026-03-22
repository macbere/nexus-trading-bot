import requests
import pandas as pd
import time
import json
import logging
from ta.trend import ADXIndicator
from ta.momentum import RSIIndicator

logger = logging.getLogger(__name__)

BLACKLIST = []


# Module-level function for easy import
def get_top_pairs(config=None, limit=50):
    """
    Standalone function to get top trading pairs.
    This wraps the MarketScanner class for easy access.
    """
    try:
        from bot.config_loader import load_config
        from bot.exchange_factory import build_exchange
        
        if config is None:
            config = load_config()
        
        exchange = build_exchange(config)
        
        # Create scanner instance
        scanner = MarketScanner(config, exchange)
        
        # Get top pairs
        pairs = scanner.scan_all_markets()
        
        # Return top N pairs
        if pairs:
            return pairs[:limit]
        return []
    except Exception as e:
        print(f"Error in get_top_pairs: {e}")
        return []


class MarketScanner:
    def __init__(self, config, exchange):
        self.config = config
        self.exchange = exchange
        self.scan_interval = 3600  # rescan every 1 hour
        self.last_scan_time = 0
        self.top_pairs = []
        self.scores = {}
        self.max_pairs = 3
        logger.info("[Scanner] Ready - will scan top 10 pairs by volume")

    def _get_top_pairs_by_volume(self, limit=50):
        """Get top pairs by 24h volume from Bitget API"""
        try:
            url = "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            
            if data.get('code') == '00000':
                tickers = data.get('data', [])
                tickers.sort(key=lambda x: float(x.get('usdtVol24h', 0)), reverse=True)
                
                top_pairs = []
                for t in tickers[:limit]:
                    symbol = t.get('symbol', '')
                    if symbol:
                        pair = symbol.replace('USDT', '') + '/USDT:USDT'
                        top_pairs.append(pair)
                
                logger.info(f"[Scanner] Top {len(top_pairs)} pairs by volume: {top_pairs}")
                return top_pairs
        except Exception as e:
            logger.error(f"[Scanner] Error fetching top pairs: {e}")
        
        # Fallback
        return [            "BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT",
            "XRP/USDT:USDT", "BNB/USDT:USDT", "DOGE/USDT:USDT",
            "ADA/USDT:USDT", "TRX/USDT:USDT", "AVAX/USDT:USDT",
            "DOT/USDT:USDT"
        ]

    def score_pair(self, symbol):
        """Score a single pair 0-100 based on profit potential."""
        try:
            from bot.exchange_factory import fetch_ohlcv_direct
            ohlcv = fetch_ohlcv_direct(symbol, "1m", limit=50)
            if not ohlcv or len(ohlcv) < 30:
                return None

            df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            close = df["close"]
            high = df["high"]
            low = df["low"]
            volume = df["volume"]

            price = float(close.iloc[-1])
            if price <= 0:
                return None

            # 1. VOLATILITY
            price_change_pct = abs(float(close.iloc[-1]) - float(close.iloc[-10])) / float(close.iloc[-10])
            volatility_score = min(price_change_pct * 10, 40)

            # 2. VOLUME
            avg_volume = float(volume.tail(10).mean())
            recent_volume = float(volume.iloc[-1])
            if recent_volume < 100000:
                return None
            if avg_volume > 0:
                volume_ratio = recent_volume / avg_volume
            else:
                volume_ratio = 0
            volume_score = min(volume_ratio * 10, 30)

            # 3. TREND STRENGTH - ADX
            try:
                adx_val = float(ADXIndicator(high, low, close, window=14).adx().iloc[-1])
                adx_score = min(adx_val / 50 * 20, 20)
            except:
                adx_score = 5
                adx_val = 0
            # 4. RSI MOMENTUM
            try:
                rsi = float(RSIIndicator(close, window=14).rsi().iloc[-1])
                rsi_distance = min(abs(rsi - 50), 30)
                rsi_score = rsi_distance / 30 * 10
            except:
                rsi_score = 3
                rsi = 50

            total_score = volatility_score + volume_score + adx_score + rsi_score

            return {
                "symbol": symbol,
                "score": round(total_score, 2),
                "price": round(price, 8),
                "volatility": round(price_change_pct, 3),
                "vol_ratio": round(volume_ratio, 2),
                "adx": round(adx_val, 1),
                "rsi": round(rsi, 1)
            }
        except Exception as e:
            logger.error(f"[Scanner] Error scoring {symbol}: {e}")
            return None

    def _count_open_positions(self):
        """Count open positions"""
        try:
            from bot.exchange_factory import get_positions, _cfg_cache
            if _cfg_cache:
                positions = get_positions(_cfg_cache)
                return len(positions)
        except Exception as e:
            logger.error(f"[Scanner] count positions error: {e}")
        return 0

    def scan_all_markets(self):
        """Scan ONLY top 10 pairs by volume - CPU optimized"""
        logger.info("[Scanner] Starting LIMITED market scan (top 10 by volume)...")
        start = time.time()

        try:
            # ONLY scan top 10 pairs by volume to save CPU
            futures = self._get_top_pairs_by_volume(limit=50)
            logger.info(f"[Scanner] Scanning ONLY {len(futures)} top pairs by volume")

            scored = []
            for symbol in futures:
                result = self.score_pair(symbol)
                if result:
                    scored.append(result)
            scored.sort(key=lambda x: x['score'], reverse=True)
            # Store just the symbol strings, not full dicts
            self.top_pairs = [item['symbol'] for item in scored[:3]]
            self.scores = {item['symbol']: item for item in scored}  # Keep full data in scores dict
            self.last_scan_time = time.time()

            logger.info(f"[Scanner] Found {len(self.top_pairs)} top pairs: {self.top_pairs}")
            logger.info(f"[Scanner] Scan completed in {time.time() - start:.2f}s")
            
            return self.top_pairs

        except Exception as e:
            logger.error(f"[Scanner] Scan error: {e}")
            return self.top_pairs

    def get_top_pairs(self):
        """Return top pairs, rescanning if 1 hour has passed."""
        now = time.time()
        if not self.top_pairs or (now - self.last_scan_time) > self.scan_interval:
            return self.scan_all_markets()
        return self.top_pairs

    def should_trade(self):
        """CRITICAL CHECK - returns True only if:
        1. We have valid top pairs
        2. Open positions < 3 (HARD LIMIT)
        """
        open_positions = self._count_open_positions()
        if open_positions >= 3:
            logger.warning(f"[Scanner] HARD LIMIT reached: {open_positions} positions")
            return False
        if not self.top_pairs:
            return False
        return True

    def get_available_pairs(self):
        """Get currently available top pairs"""
        if not self.top_pairs:
            return []
        return self.top_pairs

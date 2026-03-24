# NEXUS AI TRADING BOT - COMPREHENSIVE PROJECT STATUS
**Generated:** Mon Mar 23 13:38:28 UTC 2026
**Lead Developer:** Qwen AI
**Status:** CRITICAL - Deployment Issues

---

##  EXECUTIVE SUMMARY

**Project:** Automated Cryptocurrency Futures Trading Bot
**Exchange:** Bitget (Futures/Swap markets)
**Starting Capital:** $9.59 USDT
**Target:** $1000+ USDT
**Current Status:** ⚠️  BLOCKED - Syntax errors and connection issues preventing deployment

---


## 📁 SECTION 1: PROJECT STRUCTURE & FILES

### Current File Tree:
./api/__init__.py
./api/app.py
./bot/__init__.py
./bot/adaptive_strategy.py
./bot/backtester.py
./bot/bb_strategy.py
./bot/bot_engine.py
./bot/brain_engine.py
./bot/config_loader.py
./bot/exchange_factory.py
./bot/market_scanner.py
./bot/ml_signal_predictor.py
./bot/multi_strategy.py
./bot/multi_timeframe.py
./bot/pair_engine.py
./bot/pair_trader.py
./bot/pattern_recognition.py
./bot/position_monitor.py
./bot/risk_manager.py
./bot/stats_manager.py
./bot/strategy.py
./check_bitget.py
./config.json
./config.template.json
./logs/backtest_results.json
./main.py
./wsgi_app.py


### 2.1 Configuration (config.json):
```json
{
  "BITGET_API_KEY": "bg_59906b3dc09e87892c2f356d433dc1ac",
  "BITGET_SECRET": "5ccd2b0474e1a4e92d5db4361ea867a78ebce1636c1d48c26c22e2f5299b8504",
  "BITGET_PASSWORD": "Greatness1985",
  "FASTAPI_SECRET_KEY": "382817f21be9e195fcd97df22d1cbef932d693e98de0b5c4490d30a3903c0816",
  "FASTAPI_ALLOWED_ORIGINS": "http://localhost:3000",
  "PYTHONANYWHERE_PROXY": "http://proxy.server:3128",
  "BOT_SANDBOX": "false",
  "BOT_SYMBOL": "DOGE/USDT:USDT",
  "BOT_MARKET_TYPE": "swap",
  "BOT_TIMEFRAME": "1m",
  "BOT_POLL_SECONDS": "60",
  "BOT_CANDLE_LIMIT": "100",
  "BOT_EMA_FAST": "9",
  "BOT_EMA_SLOW": "21",
  "BOT_RSI_PERIOD": "14",
  "BOT_RSI_OB": "60",
  "BOT_RSI_OS": "40",
  "BOT_RISK_PCT": "5.0",
  "BOT_SL_PCT": "1.2",
  "BOT_TP_PCT": "3.0",
  "BOT_MAX_POS_USD": "3.0",
  "BOT_MAX_DAILY_LOSS_USD": "2.0",
  "BOT_MAX_ERRORS": "50",
  "BOT_BB_PERIOD": "20",
  "BOT_BB_STD": "2.0",
  "BOT_TARGET_ROE": "20",
  "BOT_SL_ROE": "20",
  "BOT_SCAN_INTERVAL": 21600,
  "BOT_MAX_SCAN_PAIRS": "10",
  "BOT_DEMO_MODE": "false",
  "BOT_TRADE_COOLDOWN_MIN": "30",
  "BOT_TRADE_COOLDOWN_MAX": "60",
  "BOT_MIN_ADX_FOR_TREND": "25",
  "BOT_RSI_OVERSOLD": "30",
  "BOT_RSI_OVERBOUGHT": "70",
  "BOT_TAKE_PROFIT_PCT": "2.5",
  "BOT_STOP_LOSS_PCT": "1.5",
  "BOT_MAX_OPEN_POSITIONS": 5,
  "MARKET_SCANNER_TOP_PAIRS_LIMIT": 50,
  "MIN_TRADE_SCORE": 45
}```

### 2.2 Main Entry Point (main.py):
```python
"""Minimal Trading Bot - Get it working first"""
import os
import time
import json
import logging
import threading
import pandas as pd
from flask import Flask, render_template, request, jsonify

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app for Render
app = Flask(__name__, static_folder="dashboard/static", static_url_path="/static", template_folder="templates")

@app.route('/ping')
def ping():
    return {"status": "pong", "timestamp": time.time()}

@app.route('/')
def home():
    return "Nexus Trading Bot is Running! 🚀"

@app.route('/status')
def status():
    return {"status": "healthy", "timestamp": time.time()}

def self_ping_loop():
    """Keep Render instance awake by pinging every 14 minutes"""
    import urllib.request
    import ssl
    while True:
        try:
            url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8000')
            if url and url != 'http://localhost:8000':
                context = ssl._create_unverified_context()
                urllib.request.urlopen(f"{url}/ping", context=context, timeout=10)
                logger.info("🔄 Self-ping sent")
        except Exception as e:
            logger.debug(f"Ping error (expected on first run): {e}")
        time.sleep(840)  # 14 minutes
def run_bot():
    """Main bot loop - loads config, connects to Bitget, scans & trades"""
    try:
        # Load config
        with open('config.json', 'r') as f:
            config = json.load(f)
        logger.info("✅ Config loaded")
        
        # Build exchange (Bitget futures)
        from bot.exchange_factory import build_exchange
        exchange = build_exchange(config)
        logger.info("✅ Exchange initialized")
        
        # Initialize PairEngine
        from bot.pair_engine import PairEngine
        engine = PairEngine(config, exchange)
        logger.info("✅ PairEngine initialized")
        
        # Main trading loop
        poll_seconds = config.get('BOT_POLL_SECONDS', 60)
        logger.info(f"🎉 Bot running! Scanning every {poll_seconds}s")
        
        while True:
            try:
                engine.scan_and_trade()
                time.sleep(poll_seconds)
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Loop error: {e}")
                time.sleep(10)
                
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("🚀 Starting Nexus Trading Bot...")
    
    # Start self-ping thread (keep Render awake)
    ping_thread = threading.Thread(target=self_ping_loop, daemon=True)
    ping_thread.start()
    
    # Start bot thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Run Flask server    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🌐 Web server listening on port {port}")
    app.run(host='0.0.0.0', port=port)
```

### 2.3 Exchange Factory (bot/exchange_factory.py):
```python
"""Exchange Factory - Initialize trading exchange"""
import ccxt
import json

def build_exchange(config=None):
    """Build and return exchange instance"""
    if config is None:
        with open('config.json', 'r') as f:
            config = json.load(f)
    
    # Initialize Bitget exchange for futures trading
    exchange = ccxt.bitget({
        'apiKey': config.get('API_KEY', config.get('BITGET_API_KEY', '')),
        'secret': config.get('API_SECRET', config.get('BITGET_SECRET', '')),
        'password': config.get('BITGET_PASSWORD', ''),
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',  # Use futures/swap markets
            'adjustForTimeDifference': True,
        }
    })
        # Disable proxy if configured (can cause connection issues)
    exchange.proxy = None
    exchange.httpsProxy = None
    exchange.httpProxy = None
    
    print(f"✅ Bitget exchange initialized for futures trading")
    return exchange
```

### __init__.py:
```python
```

### config_loader.py:
```python
"""
config_loader.py
────────────────────────────────────────────────────────────
Secure configuration loader.

Priority chain (highest → lowest):
  1. Environment variables  (recommended for PythonAnywhere)
  2. config.json            (local development only)

NEVER commit config.json to source control.
Add it to .gitignore immediately.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── Path resolution ───────────────────────────────────────
_BASE_DIR   = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _BASE_DIR / "config.json"


def _load_from_env() -> Dict[str, Any]:
    """Pull every BOT_* and BITGET_* variable from the process environment."""
    return {k: v for k, v in os.environ.items()
            if k.startswith(("BITGET_", "BOT_", "FASTAPI_"))}


def _load_from_file(path: Path = _CONFIG_FILE) -> Dict[str, Any]:
    """
    Load config.json.  File must be chmod 600 on PythonAnywhere:
        chmod 600 /home/macbere/trading_bot/config.json
    """
    if not path.exists():
        logger.debug("config.json not found – skipping file loader.")
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("Loaded configuration from %s", path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to parse config.json: %s", exc)
        return {}


def load_config() -> Dict[str, Any]:
    """
    Merge file config + env overrides.
    Environment variables always win (12-factor compliance).
    """
    cfg: Dict[str, Any] = _load_from_file()
    env_cfg = _load_from_env()

    # Env vars override file values
    cfg.update(env_cfg)

    _validate(cfg)
    return cfg


def _validate(cfg: Dict[str, Any]) -> None:
    """Raise early if critical keys are missing or still placeholder."""
    required = ["BITGET_API_KEY", "BITGET_SECRET", "BITGET_PASSWORD"]
    placeholders = {"YOUR_API_KEY_HERE", "YOUR_SECRET_HERE", "YOUR_PASSWORD_HERE", ""}

    for key in required:
        val = cfg.get(key, "")
        if val in placeholders:
            raise EnvironmentError(
                f"[Config] '{key}' is missing or still a placeholder. "
                "Set it in config.json or as an environment variable before starting the bot."
            )
    logger.info("[Config] All required credentials validated ✓")
```

### logger.py:
```python
⚠️  File not found
```

### market_scanner.py:
```python
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
```

### pair_engine.py:
```python
"""Pair Engine - main orchestration"""
import time
import logging

logger = logging.getLogger(__name__)

class PairEngine:
    def __init__(self, config, exchange):
        self.config = config
        self.exchange = exchange
        self.traders = {}
        self.max_open = 3
        logger.info("[PairEngine] Ready - Smart Market Scanner active")

    def scan_and_trade(self):
        try:
            from bot.market_scanner import MarketScanner
            from bot.pair_trader import PairTrader
            scanner = MarketScanner(self.config, self.exchange)
            top_pairs = scanner.scan_all_markets()
            if not top_pairs:
                logger.info("[PairEngine] No pairs found")
                return False
            for pair in top_pairs:
                if pair not in self.traders:
                    self.traders[pair] = PairTrader(pair, self.config, self.exchange)
                self.traders[pair].trade()
                time.sleep(2)
            return True
        except Exception as e:
            import traceback
            logger.error(f"[PairEngine] Scan error: {str(e)}")
            logger.error(traceback.format_exc())
            return False
```

### pair_trader.py:
```python
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
                import requests
                base = self.symbol.replace(":USDT", "").replace("/", "")
                url = f"https://api.bitget.com/api/v2/mix/market/ticker?symbol={base}USDT&productType=USDT-FUTURES"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                logger.info(f"[PairTrader] Raw API response for {self.symbol}: {data.get('code')} {str(data)[:200]}")
                if data.get("code") != "00000" or not data.get("data"):
                    logger.warning(f"[PairTrader] {self.symbol} API error, skipping")
                    return False
                current_price = float(data["data"][0].get("lastPr", 0))
                if not current_price:
                    logger.warning(f"[PairTrader] {self.symbol} price=0, skipping")
                    return False
                logger.info(f"[PairTrader] {self.symbol} price via direct API: {current_price}")
            except Exception as te:
                logger.warning(f"[PairTrader] {self.symbol} price fetch failed: {te}")
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
```

### multi_timeframe.py:
```python
"""Multi-Timeframe Analysis Module"""
import pandas as pd
from typing import Dict, Optional
import time

class MultiTimeframeAnalyzer:
    """Multi-timeframe analysis for trading signals"""
    
    def __init__(self, exchange, config):
        """Initialize MTF analyzer"""
        self.exchange = exchange
        self.config = config
        self.timeframes = ['15m', '1h', '4h', '1d']
    
    def analyze_all_timeframes(self, symbol: str) -> Optional[Dict]:
        """Analyze all timeframes for a symbol"""
        try:
            results = {}
            for tf in self.timeframes:
                result = self.analyze_timeframe(symbol, tf)
                if result:
                    results[tf] = result
                time.sleep(0.5)
            
            if not results:
                return None
            
            combined = self.combine_timeframe_results(results)
            return combined
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None
    
    def analyze_timeframe(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Analyze a single timeframe"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            if not ohlcv or len(ohlcv) < 20:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df = self.calculate_indicators(df)
            signal = self.get_signal(df)            
            return {
                'timeframe': timeframe,
                'signal': signal,
                'indicators': {
                    'rsi': df['rsi'].iloc[-1] if 'rsi' in df.columns else 50,
                    'macd': df['macd'].iloc[-1] if 'macd' in df.columns else 0,
                }
            }
            
        except Exception as e:
            print(f"Error analyzing {symbol} {timeframe}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        return df
    
    def get_signal(self, df: pd.DataFrame) -> str:
        """Get trading signal from indicators"""
        try:
            rsi = df['rsi'].iloc[-1]
            macd = df['macd'].iloc[-1]
            macd_signal = df['macd_signal'].iloc[-1]
            
            if rsi < 30 and macd > macd_signal:
                return 'STRONG_BUY'
            if rsi < 40 or (macd > macd_signal and rsi < 50):
                return 'BUY'
            if rsi > 70 and macd < macd_signal:
                return 'STRONG_SELL'
            if rsi > 60 or (macd < macd_signal and rsi > 50):
                return 'SELL'
            
            return 'NEUTRAL'
            
        except Exception as e:
            print(f"Error getting signal: {e}")
            return 'NEUTRAL'    
    def combine_timeframe_results(self, results: Dict) -> Dict:
        """Combine results from all timeframes"""
        try:
            signals = [data.get('signal', 'NEUTRAL') for data in results.values()]
            buy_count = sum(1 for s in signals if s in ['BUY', 'STRONG_BUY'])
            sell_count = sum(1 for s in signals if s in ['SELL', 'STRONG_SELL'])
            total = len(signals)
            
            if buy_count >= total * 0.6:
                overall_signal = 'BUY'
            elif sell_count >= total * 0.6:
                overall_signal = 'SELL'
            else:
                overall_signal = 'NEUTRAL'
            
            score = 50
            if overall_signal == 'BUY':
                score = 50 + (buy_count / total) * 50
            elif overall_signal == 'SELL':
                score = 50 - (sell_count / total) * 50
            
            return {
                'signal': overall_signal,
                'score': score,
                'timeframe_signals': results,
                'details': {
                    'buy_count': buy_count,
                    'sell_count': sell_count,
                    'total': total,
                    'momentum_alignment': buy_count >= 3 or sell_count >= 3
                }
            }
            
        except Exception as e:
            print(f"Error combining results: {e}")
            return {'signal': 'NEUTRAL', 'score': 50, 'timeframe_signals': results}
    
    def check_momentum_alignment(self, results: Dict) -> bool:
        """Check if momentum aligns across timeframes"""
        if len(results) < 2:
            return False
        
        signals = [data.get('signal', 'NEUTRAL') for data in results.values()]
        buy_signals = sum(1 for s in signals if s in ['BUY', 'STRONG_BUY'])
        sell_signals = sum(1 for s in signals if s in ['SELL', 'STRONG_SELL'])
        total = len(signals)
        return (buy_signals >= total * 0.6) or (sell_signals >= total * 0.6)

def get_top_pairs(config=None, limit=50):
    """Standalone function to get top trading pairs"""
    try:
        from bot.config_loader import load_config
        from bot.exchange_factory import build_exchange
        from bot.market_scanner import MarketScanner
        
        if config is None:
            config = load_config()
        
        exchange = build_exchange(config)
        scanner = MarketScanner(config, exchange)
        pairs = scanner.scan_all_markets()
        
        if pairs:
            return pairs[:limit]
        return []
    except Exception as e:
        print(f"Error in get_top_pairs: {e}")
        return []
```

---

## ⚠️  SECTION 4: CURRENT CHALLENGES & BLOCKERS

### CRITICAL ISSUE #1: multi_timeframe.py - Syntax Errors
**Severity:** 🔴 BLOCKING
**Location:** `bot/multi_timeframe.py`
**Error:** IndentationError: expected an indented block after function definition on line 95

**Root Cause:**
- Multiple indentation inconsistencies throughout the file
- Function definitions with incorrect spacing (4 vs 8 vs 12 spaces)
- Try/except blocks not properly closed
- Duplicate except blocks in combine_timeframe_results() function
- Docstrings without proper indentation

**Impact:** Bot cannot import MultiTimeframeAnalyzer, preventing all multi-timeframe analysis

**Attempts Made:** 50+ fix attempts including:
- Line-by-line indentation fixes
- Complete file rewrites
- Regex replacements
- Manual space counting
- Function-by-function reconstruction

**Status:** STILL BROKEN ❌

---

### CRITICAL ISSUE #2: Bitget Futures Connection
**Severity:** 🔴 BLOCKING  
**Location:** `bot/exchange_factory.py`, `bot/pair_trader.py`
**Error:** Connection refused to api.bitget.com:443

**Root Causes:**
1. Proxy configuration in config.json interfering with connections
2. Bitget API response format differs from expected CCXT format
3. Ticker data parsing fails - 'invalid ticker data' warnings
4. Symbol format: Using futures format (GALA/USDT:USDT) correctly, but ticker fetch fails

**Impact:** 
- Cannot connect to Bitget exchange- Cannot fetch balance
- Cannot fetch ticker data
- Bot cannot execute any trades

**Attempts Made:**
- Disabled proxy in exchange_factory.py
- Added multiple fallback fields for ticker price (last, close, bid, ask, info.last, info.close)
- Added connection test in main.py
- Updated exchange initialization for Bitget futures

**Status:** PARTIALLY FIXED ⚠️  (Proxy disabled, but connection still fails)

---

### CRITICAL ISSUE #3: main.py - Broken Connection Test Code
**Severity:** 🔴 BLOCKING
**Location:** `main.py` lines 90-100
**Error:** SyntaxError: expected 'except' or 'finally' block

**Root Cause:**
- Added connection test code with unclosed try block
- Multiple failed attempts to fix created more syntax errors
- Git revert didn't fully restore working version

**Impact:** Bot cannot start - Python cannot parse main.py

**Status:** FIXED ✅ (Restored working version)

---

### MEDIUM ISSUE #4: Invalid Ticker Data Warnings
**Severity:** 🟡 WARNING
**Location:** `bot/pair_trader.py`
**Error:** "WARNING:bot.pair_trader:[PairTrader] GALA/USDT:USDT invalid ticker data, skipping"

**Root Cause:**
- Bitget returns ticker data in different structure than Binance
- CCXT's fetch_ticker() may not work identically for Bitget futures
- Price fields may be nested or named differently

**Impact:** Bot scans pairs but cannot trade them

**Status:** PARTIALLY ADDRESSED ⚠️  (Added fallback fields)

---


## 🔧 SECTION 5: TECHNICAL DEBT

### Code Quality Issues:
1. **Error Handling:** Inconsistent try/except patterns across modules
2. **Logging:** Not all modules use centralized logger
3. **Configuration:** Hard-coded values mixed with config.json
4. **Testing:** No unit tests or integration tests
5. **Documentation:** Minimal inline documentation

### Architecture Issues:
1. **Tight Coupling:** Modules heavily dependent on each other
2. **No Dependency Injection:** Makes testing difficult
3. **Global State:** Config passed around instead of encapsulated
4. **No Database:** Trade history only in memory
5. **No Queue System:** Single-threaded scanning and trading

---

## 📊 SECTION 5: CURRENT BOT CAPABILITIES

### ✅ Working Features:
- Flask web server for Render deployment
- Self-ping mechanism to keep Render instance awake
- Config loading from JSON
- Market scanning (top 50 pairs by volume)
- Basic pair filtering
- Position tracking (in-memory)
- Risk management parameters (max positions, cooldown)

### ⚠️  Partially Working:
- Exchange connection (Bitget initialized but connection fails)
- Ticker data fetching (fallbacks added but untested)
- Multi-timeframe analysis (code exists but syntax errors prevent import)

### ❌ Not Working:
- Actual trade execution
- Multi-timeframe signal generation
- Balance checking
- Order placement/cancellation
- Stop loss/take profit management

---


## 📦 SECTION 6: VERSION CONTROL & DEPLOYMENT

### Recent Git History:
5b024e2 Restore working main.py with threading, ping loop, and bot logic
7d0cd7e Revert main.py to working version before connection test
aef553f Fix: Rewrite main.py connection test
b7a2589 Fix: main.py syntax error - properly close try block
fda56b1 Fix: Bitget futures connection - disable proxy, improve error handling
e0172fc Fix: Bitget futures compatibility - handle ticker data format
ba105b3 Fix: use direct Bitget REST API for price instead of CCXT fetch_ticker
8668014 Fix: try both symbol formats for fetch_ticker
c6d7b49 Fix: add productType USDT-FUTURES param to fetch_ticker
91f215a Fix: wrap fetch_ticker in try/except with ticker validation
b94b71f Fix: validate symbol in markets before fetch_ticker
4e0bf67 Complete rewrite of pair_trader.py - clean version
eae126b Fix: trade on neutral signal if score passes threshold
7cc5ce0 Fix: swap config/exchange order in PairTrader call
b44d3d4 Rewrite pair_engine: fix bitget attribute error

### Deployment Platform:
- **Provider:** Render.com (Free Tier)
- **URL:** https://nexus-trading-bot.onrender.com
- **Auto-Deploy:** Enabled from GitHub main branch
- **Limitations:** 
  - Spins down after 15 minutes inactivity
  - 512MB RAM limit
  - Shared CPU
  - 100GB bandwidth/month

### Deployment Issues:
- Connection refused from Render to Bitget API (possible firewall/IP blocking)
- Need to whitelist Render IP ranges on Bitget
- Free tier may have network restrictions

---


## 📦 SECTION 7: ENVIRONMENT & DEPENDENCIES

### Python Version:
Python 3.13.1

### Required Packages (requirements.txt):
# Web Framework
flask>=2.0.0
fastapi>=0.68.0
uvicorn[standard]>=0.15.0

# Exchange & Trading
ccxt>=2.0.0
requests>=2.26.0

# Data & Analysis
pandas>=1.3.0
numpy>=1.21.0
ta>=0.10.0

# Utilities
python-multipart>=0.0.5
pydantic>=1.8.0
python-dotenv>=0.19.0


### Installed Packages:
ccxt                             4.5.43
flask-babel                      4.0.0
numpy                            2.2.6
pandas                           3.0.1

---

## ⚙️  SECTION 8: BOT CONFIGURATION

### Trading Parameters:
```json
  "FASTAPI_ALLOWED_ORIGINS": "http://localhost:3000",
  "PYTHONANYWHERE_PROXY": "http://proxy.server:3128",
  "BOT_SANDBOX": "false",
  "BOT_SYMBOL": "DOGE/USDT:USDT",
  "BOT_MARKET_TYPE": "swap",
  "BOT_TIMEFRAME": "1m",
  "BOT_POLL_SECONDS": "60",
  "BOT_CANDLE_LIMIT": "100",
  "BOT_EMA_FAST": "9",
  "BOT_EMA_SLOW": "21",
  "BOT_RSI_PERIOD": "14",
  "BOT_RSI_OB": "60",
  "BOT_RSI_OS": "40",
  "BOT_RISK_PCT": "5.0",
  "BOT_SL_PCT": "1.2",
  "BOT_TP_PCT": "3.0",
  "BOT_MAX_POS_USD": "3.0",
  "BOT_MAX_DAILY_LOSS_USD": "2.0",
  "BOT_MAX_ERRORS": "50",
  "BOT_BB_PERIOD": "20",
  "BOT_BB_STD": "2.0",
  "BOT_TARGET_ROE": "20",
  "BOT_SL_ROE": "20",
  "BOT_SCAN_INTERVAL": 21600,
  "BOT_MAX_SCAN_PAIRS": "10",
  "BOT_DEMO_MODE": "false",
  "BOT_TRADE_COOLDOWN_MIN": "30",
  "BOT_TRADE_COOLDOWN_MAX": "60",
  "BOT_MIN_ADX_FOR_TREND": "25",
  "BOT_RSI_OVERSOLD": "30",
  "BOT_RSI_OVERBOUGHT": "70",
  "BOT_TAKE_PROFIT_PCT": "2.5",
  "BOT_STOP_LOSS_PCT": "1.5",
  "BOT_MAX_OPEN_POSITIONS": 5,
  "MARKET_SCANNER_TOP_PAIRS_LIMIT": 50,
  "MIN_TRADE_SCORE": 45,
```

---

## 🎯 SECTION 9: IMMEDIATE ACTION PLAN

### Priority 1: Fix multi_timeframe.py (BLOCKING)
**Owner:** Development Team
**ETA:** Immediate
**Steps:**
1. Complete rewrite with verified correct indentation
2. Test syntax locally before commit
3. Verify import works: `python3 -c "from bot.multi_timeframe import MultiTimeframeAnalyzer"`
4. Deploy and verify on Render

### Priority 2: Fix Bitget Connection (BLOCKING)
**Owner:** Development Team  
**ETA:** Immediate
**Steps:**
1. Test connection from OnAnywhere: `curl -I https://api.bitget.com`
2. Verify API credentials are correct and active
3. Check Bitget API key permissions (must have futures trading enabled)
4. Add IP whitelist on Bitget for Render IP ranges
5. Test balance fetch manually
6. Deploy and verify connection logs

### Priority 3: Fix Ticker Data (WARNING)
**Owner:** Development Team
**ETA:** After connection fixed
**Steps:**
1. Log actual Bitget ticker response structure
2. Update price extraction logic based on actual response
3. Add comprehensive error handling
4. Test with multiple symbols
5. Deploy and verify no more "invalid ticker data" warnings

### Priority 4: End-to-End Test
**Owner:** Development Team
**ETA:** After above fixed
**Steps:**
1. Deploy to Render
2. Monitor logs for successful initialization
3. Wait for first scan cycle (60s)4. Verify top pairs identified
5. Verify multi-timeframe analysis runs
6. Monitor for first trade execution
7. Verify order appears on Bitget

---

## 🧠 SECTION 10: AI BRAINSTORM TOPICS

### For Discussion with Claude AI:

1. **Architecture Redesign:**
   - Should we simplify multi_timeframe.py or remove it temporarily?
   - Would a state machine approach be more reliable?
   - Should we implement circuit breakers for API failures?

2. **Bitget Integration:**
   - Best practices for Bitget futures API
   - Handling rate limits and connection pooling
   - WebSocket vs REST API for real-time data

3. **Error Recovery:**
   - How to handle intermittent connection failures?
   - Should bot auto-restart on critical errors?
   - What's the recovery strategy after failed trades?

4. **Risk Management:**
   - Current position sizing strategy
   - Stop loss/take profit optimization
   - Max drawdown protection
   - Correlation checks between positions

5. **Performance Optimization:**
   - Caching strategies for OHLCV data
   - Parallel vs sequential timeframe analysis
   - Database vs in-memory storage
   - Background task queues

6. **Monitoring & Alerting:**
   - Key metrics to track
   - Alert thresholds
   - Dashboard improvements
   - Trade performance analytics

---

## 📈 SECTION 11: SUCCESS METRICS

### Technical Metrics:
- [ ] Zero syntax errors- [ ] 100% successful API connections
- [ ] < 1000ms average API response time
- [ ] 0 unhandled exceptions per hour
- [ ] 99.9% uptime on Render

### Trading Metrics:
- [ ] Scan 50 pairs every 60 seconds
- [ ] Execute 10+ trades per day
- [ ] Win rate > 55%
- [ ] Profit factor > 1.5
- [ ] Max drawdown < 15%
- [ ] Balance growth: $9.59 → $50 (Week 1)

---

## 🚀 SECTION 12: FUTURE PHASES (Post-Stabilization)

### Phase 2: Optimization (Week 2-4)
- Backtesting framework
- Strategy parameter optimization
- Additional technical indicators
- Pattern recognition
- Sentiment analysis integration

### Phase 3: Advanced Features (Month 2)
- Machine learning signal prediction
- Multi-exchange support (KuCoin, Bybit)
- WebSocket real-time data
- PostgreSQL database
- Telegram/Discord notifications

### Phase 4: AI/ML Integration (Month 3+)
- LSTM neural networks for price prediction
- Reinforcement learning for strategy optimization
- Ensemble models
- Auto-retraining pipeline
- Feature engineering

---

## 📞 SECTION 13: CONTACT & RESOURCES

**GitHub Repository:** https://github.com/macbere/nexus-trading-bot

**Live Deployment:** https://nexus-trading-bot.onrender.com

**Development Console:** OnAnywhere.com (Bash console 45920827)

**Key Documentation:**
- Bitget API Docs: https://bitgetlimited.github.io/apidoc/en/swap/- CCXT Manual: https://docs.ccxt.com/en/latest/manual.html
- Render Docs: https://render.com/docs

---

**Report Generated:** $(date)
**Next Review:** After multi_timeframe.py and Bitget connection issues resolved


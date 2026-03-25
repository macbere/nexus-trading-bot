"""
Exchange Factory - Direct REST API for Bitget Futures
Bypasses ccxt entirely for Render/PythonAnywhere free tier compatibility
"""
import hmac
import hashlib
import base64
import time
import json
import requests
import logging

logger = logging.getLogger(__name__)

_cfg_cache = None


def build_exchange(config=None):
    """Returns config dict as the exchange object. All API calls use direct REST."""
    global _cfg_cache
    if config is None:
        with open("config.json", "r") as f:
            config = json.load(f)
    _cfg_cache = config
    logger.info("✅ Bitget direct REST API initialized")
    return config


def _sign_request(cfg, method, path, body_str=""):
    """Generate Bitget API HMAC-SHA256 signature"""
    timestamp = str(int(time.time() * 1000))
    msg = timestamp + method.upper() + path + body_str
    secret = cfg.get("BITGET_SECRET", "")
    sign = base64.b64encode(
        hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()
    headers = {
        "ACCESS-KEY": cfg.get("BITGET_API_KEY", ""),
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": cfg.get("BITGET_PASSWORD", ""),
        "Content-Type": "application/json",
        "locale": "en-US",
    }
    return headers


def get_balance(cfg):
    """Fetch USDT futures balance via direct REST API"""
    try:
        path = "/api/v2/mix/account/account"
        params = "?symbol=BTCUSDT&productType=USDT-FUTURES&marginCoin=USDT"
        headers = _sign_request(cfg, "GET", path + params)
        resp = requests.get(
            f"https://api.bitget.com{path}{params}",
            headers=headers,
            timeout=10
        )
        data = resp.json()
        if data.get("code") == "00000":
            info = data.get("data", {})
            available = float(info.get("available", 0))
            equity = float(info.get("accountEquity", available))
            logger.info(f"[Exchange] Balance: {equity:.4f} USDT | Free: {available:.4f}")
            return {"total": equity, "free": available}
        else:
            logger.error(f"[Exchange] Balance error: {data.get('msg')}")
            return {"total": 0.0, "free": 0.0}
    except Exception as e:
        logger.error(f"[Exchange] Balance fetch failed: {e}")
        return {"total": 0.0, "free": 0.0}


def get_positions(cfg):
    """Fetch open futures positions via direct REST API"""
    try:
        path = "/api/v2/mix/position/all-position"
        params = "?productType=USDT-FUTURES&marginCoin=USDT"
        headers = _sign_request(cfg, "GET", path + params)
        resp = requests.get(
            f"https://api.bitget.com{path}{params}",
            headers=headers,
            timeout=10
        )
        data = resp.json()
        if data.get("code") == "00000":
            positions = data.get("data", [])
            open_pos = [p for p in positions if float(p.get("total", 0)) > 0]
            return open_pos
        return []
    except Exception as e:
        logger.error(f"[Exchange] Positions fetch failed: {e}")
        return []


def fetch_ohlcv_direct(symbol, timeframe="1m", limit=100):
    """
    Fetch OHLCV candles via direct Bitget REST API.
    symbol: BTC/USDT:USDT or BTCUSDT
    timeframe: 1m, 5m, 15m, 1h, 4h, 1d etc
    """
    try:
        # Convert symbol format: BTC/USDT:USDT -> BTCUSDT
        raw = symbol.replace(":USDT", "").replace("/", "")

        # Bitget v2 granularity map - exact values required by API
        granularity_map = {
            "1m":  "1m",
            "3m":  "3m",
            "5m":  "5m",
            "15m": "15m",
            "30m": "30m",
            "1h":  "1H",
            "2h":  "2H",
            "4h":  "4H",
            "6h":  "6H",
            "12h": "12H",
            "1d":  "1Dutc",
            "1w":  "1Wutc",
        }
        granularity = granularity_map.get(timeframe.lower(), "1m")

        url = (
            f"https://api.bitget.com/api/v2/mix/market/candles"
            f"?symbol={raw}&productType=USDT-FUTURES"
            f"&granularity={granularity}&limit={limit}"
        )
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if data.get("code") == "00000":
            candles = data.get("data", [])
            result = []
            for c in candles:
                result.append([
                    int(c[0]),      # timestamp
                    float(c[1]),    # open
                    float(c[2]),    # high
                    float(c[3]),    # low
                    float(c[4]),    # close
                    float(c[5]),    # volume
                ])
            return result
        else:
            logger.warning(
                f"[Exchange] OHLCV error for {symbol}: {data.get('msg')}"
            )
            return []
    except Exception as e:
        logger.error(f"[Exchange] OHLCV fetch failed for {symbol}: {e}")
        return []


def place_order_direct(cfg, symbol, side, size, order_type="market"):
    """
    Place futures order via direct REST API.
    symbol: BTC/USDT:USDT -> BTCUSDT
    side: buy or sell
    size: quantity as float
    """
    try:
        raw_symbol = symbol.replace(":USDT", "").replace("/", "")
        body = {
            "symbol": raw_symbol,
            "productType": "USDT-FUTURES",
            "marginMode": "crossed",
            "marginCoin": "USDT",
            "size": str(size),
            "side": side.lower(),
            "orderType": order_type,
        }
        body_str = json.dumps(body)
        path = "/api/v2/mix/order/place-order"
        headers = _sign_request(cfg, "POST", path, body_str)
        resp = requests.post(
            f"https://api.bitget.com{path}",
            headers=headers,
            data=body_str,
            timeout=10
        )
        result = resp.json()
        if result.get("code") == "00000":
            order_id = result.get("data", {}).get("orderId", "unknown")
            logger.info(
                f"[Exchange] ✅ Order placed: {side} {size} {symbol} | ID: {order_id}"
            )
            return result.get("data", {})
        else:
            logger.error(
                f"[Exchange] ❌ Order failed: {result.get('msg')} | {result}"
            )
            return None
    except Exception as e:
        logger.error(f"[Exchange] Order placement exception: {e}")
        return None

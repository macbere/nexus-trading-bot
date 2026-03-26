"""
Exchange Factory - Direct REST API for Bitget Futures
Complete definitive version - all bugs fixed
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
_precision_cache = {}


def build_exchange(config=None):
    global _cfg_cache
    if config is None:
        with open("config.json", "r") as f:
            config = json.load(f)
    _cfg_cache = config
    logger.info("✅ Bitget direct REST API initialized")
    return config


def _sign_request(cfg, method, path, body_str=""):
    timestamp = str(int(time.time() * 1000))
    msg = timestamp + method.upper() + path + body_str
    secret = cfg.get("BITGET_SECRET", "")
    sign = base64.b64encode(
        hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "ACCESS-KEY": cfg.get("BITGET_API_KEY", ""),
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": cfg.get("BITGET_PASSWORD", ""),
        "Content-Type": "application/json",
        "locale": "en-US",
    }


def _get_price_decimals(symbol):
    """
    Get exact decimal places required by Bitget for TP/SL prices.
    Uses contract API with hardcoded fallback for reliability.
    """
    global _precision_cache
    raw = symbol.replace("/USDT:USDT", "USDT").replace("/", "").upper()

    # Hardcoded fallback map - verified from Bitget checkScale errors
    KNOWN_DECIMALS = {
        "BTCUSDT":  1, "ETHUSDT":  2, "SOLUSDT":  2,
        "BNBUSDT":  2, "XRPUSDT":  4, "ADAUSDT":  4,
        "DOGEUSDT": 5, "LTCUSDT":  2, "DOTUSDT":  3,
        "LINKUSDT": 3, "UNIUSDT":  3, "AVAXUSDT": 2,
        "ATOMUSDT": 3, "FILUSDT":  4, "AAVEUSDT": 2,
        "ICPUSDT":  3, "ETCUSDT":  3, "TRXUSDT":  5,
        "XLMUSDT":  5, "BCHUSDT":  2, "APEUSDT":  4,
        "GMTUSDT":  5, "ZILUSDT":  6, "IOSTUSDT": 6,
        "RUNEUSDT": 4, "KNCUSDT":  4, "APTUSDT":  3,
        "CHZUSDT":  5, "NEARUSDT": 4, "SANDUSDT": 5,
        "GALUSDT":  5, "DYDXUSDT": 4, "CRVUSDT":  4,
        "EGLDUSDT": 3, "KSMUST":   3, "ALGOUSDT": 5,
        "IOTAUSDT": 5, "ENJUSDT":  5, "FTMUSDT":  5,
        "INJUSDT":  3, "OPUSDT":   4, "ARBUSDT":  4,
        "LDOUSDT":  4, "STXUSDT":  4, "SUSHIUSDT":4,
        "XTZUSDT":  4, "UNIUSDT":  4, "THETAUSDT":4,
        "AXSUSDT":  3, "DASHUSDT": 3, "MANAUSDT": 5,
        "PEOPLEUSDT":5,"NEOUSDT":  3, "ALICEUSDT":4,
        "WAVESUSDT":4, "BNBUSDT":  2, "IMUSDT":   5,
    }

    if raw in KNOWN_DECIMALS:
        return KNOWN_DECIMALS[raw]

    # Try API if not in known list
    if not _precision_cache:
        try:
            url = "https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES"
            resp = requests.get(url, timeout=10).json()
            if resp.get("code") == "00000":
                for c in resp.get("data", []):
                    sym = c.get("symbol", "").upper()
                    place = int(c.get("pricePlace", 4))
                    _precision_cache[sym] = place
        except Exception as e:
            logger.error(f"[Exchange] Precision fetch error: {e}")

    return _precision_cache.get(raw, 4)


def get_balance(cfg):
    try:
        path = "/api/v2/mix/account/account"
        params = "?symbol=BTCUSDT&productType=USDT-FUTURES&marginCoin=USDT"
        headers = _sign_request(cfg, "GET", path + params)
        resp = requests.get(f"https://api.bitget.com{path}{params}", headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == "00000":
            info = data.get("data", {})
            available = float(info.get("available", 0))
            equity = float(info.get("accountEquity", available))
            logger.info(f"[Exchange] Balance: {equity:.4f} USDT | Free: {available:.4f}")
            return {"total": equity, "free": available}
        logger.error(f"[Exchange] Balance error: {data.get('msg')}")
        return {"total": 0.0, "free": 0.0}
    except Exception as e:
        logger.error(f"[Exchange] Balance fetch failed: {e}")
        return {"total": 0.0, "free": 0.0}


def get_positions(cfg):
    try:
        path = "/api/v2/mix/position/all-position"
        params = "?productType=USDT-FUTURES&marginCoin=USDT"
        headers = _sign_request(cfg, "GET", path + params)
        resp = requests.get(f"https://api.bitget.com{path}{params}", headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == "00000":
            return [p for p in data.get("data", []) if float(p.get("total", 0)) > 0]
        return []
    except Exception as e:
        logger.error(f"[Exchange] Positions fetch failed: {e}")
        return []


def fetch_ohlcv_direct(symbol, timeframe="1m", limit=100):
    try:
        raw = symbol.replace("/USDT:USDT", "USDT").replace("/", "")
        granularity_map = {
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H",
            "1d": "1Dutc", "1w": "1Wutc",
        }
        granularity = granularity_map.get(timeframe.lower(), "1m")
        url = (
            f"https://api.bitget.com/api/v2/mix/market/candles"
            f"?symbol={raw}&productType=USDT-FUTURES&granularity={granularity}&limit={limit}"
        )
        data = requests.get(url, timeout=10).json()
        if data.get("code") == "00000":
            return [[int(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])] for c in data.get("data", [])]
        logger.warning(f"[Exchange] OHLCV error for {symbol}: {data.get('msg')}")
        return []
    except Exception as e:
        logger.error(f"[Exchange] OHLCV fetch failed for {symbol}: {e}")
        return []


def place_order_direct(cfg, symbol, side, size, order_type="market"):
    try:
        raw_symbol = symbol.replace("/USDT:USDT", "USDT").replace("/", "")
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
        resp = requests.post(f"https://api.bitget.com{path}", headers=headers, data=body_str, timeout=10)
        result = resp.json()
        if result.get("code") == "00000":
            order_id = result.get("data", {}).get("orderId", "unknown")
            logger.info(f"[Exchange] ✅ Order placed: {side} {size} {symbol} | ID: {order_id}")
            return result.get("data", {})
        logger.error(f"[Exchange] ❌ Order failed: {result.get('msg')} | {result}")
        return None
    except Exception as e:
        logger.error(f"[Exchange] Order placement exception: {e}")
        return None


def place_tpsl_direct(cfg, symbol, side, entry_price, tp_pct=0.025, sl_pct=0.015, size=None):
    """
    Official Bitget API v2 place-tpsl-order format.
    CRITICAL: symbol must be LOWERCASE (e.g. bnbusdt not BNBUSDT)
    productType: usdt-futures (lowercase)
    planType: profit_plan | loss_plan
    executePrice: 0 = market execution
    rangeRate: empty string required
    """
    try:
        raw_symbol = symbol.replace("/USDT:USDT", "USDT").replace("/", "").lower()
        decimals = _get_price_decimals(symbol)

        # Fetch actual position data
        actual_hold_side = None
        actual_size = None
        try:
            positions = get_positions(cfg)
            sym_upper = raw_symbol.upper()
            for p in positions:
                if sym_upper in p.get("symbol", "").upper():
                    actual_hold_side = p.get("holdSide", "").lower()
                    actual_size = str(p.get("total", "1"))
                    break
        except Exception:
            pass

        hold_side = actual_hold_side if actual_hold_side else ("long" if side.lower() == "buy" else "short")
        pos_size = actual_size if (actual_size and float(actual_size) > 0) else (str(size) if size else "1")

        if hold_side == "long":
            tp_price = round(entry_price * (1 + tp_pct), decimals)
            sl_price = round(entry_price * (1 - sl_pct), decimals)
        else:
            tp_price = round(entry_price * (1 - tp_pct), decimals)
            sl_price = round(entry_price * (1 + sl_pct), decimals)

        logger.info(f"[Exchange] TPSL: {raw_symbol} TP:{tp_price} SL:{sl_price} size:{pos_size} side:{hold_side}")

        path = "/api/v2/mix/order/place-tpsl-order"
        results = []

        for label, trigger_price, plan_type in [
            ("TP", tp_price, "profit_plan"),
            ("SL", sl_price, "loss_plan"),
        ]:
            body = {
                "symbol":       raw_symbol,
                "productType":  "usdt-futures",
                "marginCoin":   "USDT",
                "planType":     plan_type,
                "triggerPrice": str(trigger_price),
                "triggerType":  "mark_price",
                "executePrice": "0",
                "holdSide":     hold_side,
                "size":         pos_size,
                "rangeRate":    "",
            }
            body_str = json.dumps(body)
            headers  = _sign_request(cfg, "POST", path, body_str)
            result   = requests.post(
                f"https://api.bitget.com{path}",
                headers=headers,
                data=body_str,
                timeout=10
            ).json()

            if result.get("code") == "00000":
                logger.info(f"[Exchange] ✅ {label} set: {symbol} @ {trigger_price}")
                results.append(True)
            else:
                logger.error(f"[Exchange] ❌ {label} failed: {result.get('msg')} | {result}")
                results.append(False)

        return all(results)

    except Exception as e:
        logger.error(f"[Exchange] TP/SL error: {e}")
        return False


def close_position_direct(cfg, symbol, hold_side, size):
    """
    Close an open position by placing a reduce-only market order.
    hold_side: long -> close with sell | short -> close with buy
    """
    try:
        raw_symbol = symbol.replace("/USDT:USDT","USDT").replace("/","")
        close_side = "sell" if hold_side == "long" else "buy"
        body = {
            "symbol":      raw_symbol,
            "productType": "USDT-FUTURES",
            "marginMode":  "crossed",
            "marginCoin":  "USDT",
            "size":        str(size),
            "side":        close_side,
            "tradeSide":   "close",
            "orderType":   "market",
        }
        body_str = json.dumps(body)
        path = "/api/v2/mix/order/place-order"
        headers = _sign_request(cfg, "POST", path, body_str)
        result = requests.post(
            f"https://api.bitget.com{path}",
            headers=headers, data=body_str, timeout=10
        ).json()
        if result.get("code") == "00000":
            logger.info(f"[Exchange] ✅ Closed: {symbol} {hold_side} size:{size}")
            return True
        else:
            logger.error(f"[Exchange] ❌ Close failed: {result.get('msg')}")
            return False
    except Exception as e:
        logger.error(f"[Exchange] Close error: {e}")
        return False

"""Exchange factory - FUTURES/SWAP ONLY - Direct API"""
import json
import ccxt
import requests
import hmac
import hashlib
import base64
import time

_exchange_cache = None
_cfg_cache = None

def _sign_request(secret, timestamp, method, path, body=""):
    msg = timestamp + method + path + body
    return base64.b64encode(
        hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()

def _get_headers(cfg, method, path, body=""):
    timestamp = str(int(time.time() * 1000))
    signature = _sign_request(
        cfg.get("BITGET_SECRET", ""),
        timestamp, method, path, body
    )
    return {
        "ACCESS-KEY":        cfg.get("BITGET_API_KEY", ""),
        "ACCESS-SIGN":       signature,
        "ACCESS-TIMESTAMP":  timestamp,
        "ACCESS-PASSPHRASE": cfg.get("BITGET_PASSWORD", ""),
        "Content-Type":      "application/json",
        "locale":            "en-US",
    }

def get_balance(cfg):
    """Get futures balance directly"""
    path = "/api/v2/mix/account/accounts?productType=USDT-FUTURES"
    resp = requests.get(
        f"https://api.bitget.com{path}",
        headers=_get_headers(cfg, "GET", path),
        timeout=10
    )
    data = resp.json()
    if data.get("code") == "00000":
        accounts = data.get("data", [])
        for acc in accounts:
            if acc.get("marginCoin") == "USDT":
                return {
                    "total":     float(acc.get("usdtEquity", 0)),
                    "free":      float(acc.get("available", 0)),
                    "used":      float(acc.get("locked", 0)),
                    "unrealized": float(acc.get("unrealizedPL", 0) or 0),
                }
    return {"total": 0, "free": 0, "used": 0, "unrealized": 0}

def get_positions(cfg):
    """Get open futures positions directly"""
    path = "/api/v2/mix/position/all-position?marginCoin=USDT&productType=USDT-FUTURES"
    resp = requests.get(
        f"https://api.bitget.com{path}",
        headers=_get_headers(cfg, "GET", path),
        timeout=10
    )
    data = resp.json()
    if data.get("code") == "00000":
        positions = data.get("data", [])
        active = []
        for p in positions:
            size = float(p.get("total", 0) or 0)
            if size > 0:
                entry  = float(p.get("openPriceAvg", 0) or 0)
                mark   = float(p.get("markPrice", entry) or entry)
                side   = p.get("holdSide", "")
                upnl   = float(p.get("unrealizedPL", 0) or 0)
                roe    = float(p.get("achievedProfits", 0) or 0)
                # Calculate ROE %
                if entry > 0 and size > 0:
                    margin = float(p.get("marginSize", 1) or 1)
                    roe_pct = (upnl / margin * 100) if margin > 0 else 0
                else:
                    roe_pct = 0
                active.append({
                    "symbol":       p.get("symbol", ""),
                    "side":         side,
                    "size":         size,
                    "entry":        entry,
                    "mark":         mark,
                    "pnl":          upnl,
                    "roe":          roe_pct,
                    "tp":           p.get("takeProfit", "NOT SET"),
                    "sl":           p.get("stopLoss", "NOT SET"),
                    "raw":          p,
                })
        return active
    return []


def fetch_ohlcv_direct(symbol, timeframe="1m", limit=50):
    """Fetch OHLCV via direct requests — bypasses ccxt HTTP (PythonAnywhere proxy-safe)"""
    tf_map = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m",
              "30m": "30m", "1h": "1H", "4h": "4H", "1d": "1D"}
    gran = tf_map.get(timeframe, "1m")
    raw_symbol = symbol.replace("/USDT:USDT", "USDT")
    url = (
        f"https://api.bitget.com/api/v2/mix/market/candles"
        f"?symbol={raw_symbol}&granularity={gran}"
        f"&limit={limit}&productType=USDT-FUTURES"
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("code") == "00000":
            candles = []
            for c in data.get("data", []):
                candles.append([
                    int(c[0]),    # timestamp
                    float(c[1]),  # open
                    float(c[2]),  # high
                    float(c[3]),  # low
                    float(c[4]),  # close
                    float(c[5]),  # volume
                ])
            return candles
    except Exception as e:
        print(f"[fetch_ohlcv_direct] {symbol} error: {e}")
    return []


def set_position_mode(cfg):
    """Set account to one-way (unilateral) position mode"""
    body_dict = {
        "productType": "USDT-FUTURES",
        "positionMode": "one_way_mode",  # or "hedge_mode"
    }
    body_str = json.dumps(body_dict)
    path = "/api/v2/mix/account/set-position-mode"
    
    headers = _get_headers(cfg, "POST", path, body_str)
    
    try:
        resp = requests.post(
            f"https://api.bitget.com{path}",
            headers=headers,
            data=body_str,
            timeout=10
        )
        result = resp.json()
        print(f"[Position Mode] Set to one-way: {result}")
        return result
    except Exception as e:
        print(f"[Position Mode ERROR] {e}")
        return {"code": "ERROR", "msg": str(e)}

def build_exchange(cfg: dict, exchange_id: str = "bitget") -> ccxt.Exchange:
    global _exchange_cache, _cfg_cache
    if _exchange_cache is not None:
        return _exchange_cache

    passphrase = cfg.get("BITGET_PASSWORD") or cfg.get("BITGET_PASSPHRASE") or ""
    api_key    = cfg.get("BITGET_API_KEY", "")
    secret     = cfg.get("BITGET_SECRET", "")

    exchange = ccxt.bitget({
        "apiKey":   api_key,
        "secret":   secret,
        "password": passphrase,
        "options": {
            "defaultType":    "swap",
            "defaultSubType": "linear",
        }
    })
    exchange.password = passphrase

    # Load futures markets via REST
    try:
        url  = "https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        contracts = data.get("data", [])
        markets = {}
        markets_by_id = {}
        for c in contracts:
            base = c.get("baseCoin", "")
            if not base:
                continue
            sym        = base + "/USDT:USDT"
            market_id  = c.get("symbol", base + "USDT")
            size_mult  = float(c.get("sizeMultiplier", 1) or 1)
            price_step = float(c.get("priceEndStep", 0.0001) or 0.0001)
            min_trade  = float(c.get("minTradeNum", 1) or 1)
            m = {
                "id": market_id, "symbol": sym,
                "base": base, "quote": "USDT",
                "settle": "USDT", "baseId": base,
                "quoteId": "USDT", "settleId": "USDT",
                "type": "swap", "swap": True,
                "spot": False, "future": False,
                "option": False, "active": True,
                "contract": True, "linear": True,
                "inverse": False,
                "precision": {
                    "amount": size_mult, "price": price_step,
                    "base": size_mult, "quote": price_step,
                },
                "limits": {
                    "leverage": {"min": 1, "max": 125},
                    "amount": {"min": min_trade, "max": None},
                    "price": {"min": None, "max": None},
                    "cost": {"min": 5.0, "max": None},
                },
                "info": c,
            }
            markets[sym] = m
            markets_by_id[market_id] = m
        if markets:
            exchange.markets       = markets
            exchange.markets_by_id = markets_by_id
            exchange.symbols       = list(markets.keys())
            exchange.ids           = list(markets_by_id.keys())
            print(f"[Exchange] {len(markets)} futures markets loaded via REST ✅")
    except Exception as e:
        print(f"[Exchange] REST load failed: {e}")

    exchange.options["defaultType"]    = "swap"
    exchange.options["defaultSubType"] = "linear"
    _exchange_cache = exchange
    _cfg_cache      = cfg
    return exchange

def get_exchange(config_path="/home/macbere/trading_bot/config.json"):
    with open(config_path) as f:
        cfg = json.load(f)
    return build_exchange(cfg), cfg

def fetch_swap_positions(exchange):
    """Use direct API - bypasses ccxt auth issues"""
    global _cfg_cache
    if _cfg_cache:
        return get_positions(_cfg_cache)
    try:
        positions = exchange.fetch_positions(
            params={"productType": "USDT-FUTURES", "marginCoin": "USDT"}
        )
        return [p for p in positions if float(p.get("contracts", 0) or 0) > 0]
    except Exception as e:
        print(f"fetch_swap_positions error: {e}")
        return []

def register_exchange(name: str, exchange_class) -> None:
    pass

def place_order_direct(cfg, symbol, side, size, order_type="market"):
    """Place futures order via direct REST API - bypasses ccxt"""
    # Convert symbol: UB/USDT:USDT -> UBUSDT
    # Handle symbol format: could be "MOODENG/USDT:USDT" or "MOODENGUSDT"
    if symbol.endswith("USDT") and "/" not in symbol:
        raw_symbol = symbol  # Already in correct format
    else:
        raw_symbol = symbol.replace("/USDT:USDT", "") + "USDT"
    print(f"[ORDER] {symbol} -> {raw_symbol} | {side.upper()} {size}")
    
    # Build request body
    body_dict = {
        "symbol": raw_symbol,
        "productType": "USDT-FUTURES",
        "marginMode": "crossed",
        "marginCoin": "USDT",
        "size": str(size),
        "side": side.lower(),
        "orderType": order_type,
    }
    
    body_str = json.dumps(body_dict)
    path = "/api/v2/mix/order/place-order"
    
    # Get headers with signature
    headers = _get_headers(cfg, "POST", path, body_str)
    
    # Make request
    try:
        resp = requests.post(
            f"https://api.bitget.com{path}",
            headers=headers,
            data=body_str,
            timeout=10
        )
        result = resp.json()
        print(f"[Order] {side.upper()} {size} {raw_symbol} -> {result}")
        return result
    except Exception as e:
        print(f"[Order ERROR] {side.upper()} {size} {raw_symbol}: {e}")
        return {"code": "ERROR", "msg": str(e)}

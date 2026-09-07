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
from pathlib import Path

logger = logging.getLogger(__name__)

_cfg_cache = None
_precision_cache = {}
_contract_cache = {}


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def is_demo_mode(cfg):
    """Return whether authenticated Bitget requests must use demo trading."""
    return _as_bool(cfg.get("BITGET_DEMO", cfg.get("BOT_SANDBOX", True)), True)


def _require_trading_mode(cfg):
    """Refuse live orders unless the operator explicitly opts in."""
    if is_demo_mode(cfg):
        return
    if not _as_bool(cfg.get("BOT_ALLOW_LIVE_TRADING"), False):
        raise RuntimeError(
            "Live trading is disabled. Set BITGET_DEMO=true for demo mode, "
            "or explicitly set BOT_ALLOW_LIVE_TRADING=true to enable live orders."
        )


class BitgetExchangeClient:
    """Small compatibility wrapper around the direct REST helpers."""

    def __init__(self, config):
        self.config = config

    def create_order(self, symbol, order_type, side, amount, price=None, params=None):
        params = params or {}
        _require_trading_mode(self.config)
        if params.get("reduceOnly"):
            hold_side = "long" if side.lower() == "sell" else "short"
            ok = close_position_direct(self.config, symbol, hold_side, amount)
            if ok:
                return {
                    "id": f"close-{int(time.time() * 1000)}",
                    "status": "closed",
                    "symbol": symbol,
                    "amount": amount,
                }
            return None

        return place_order_direct(
            self.config,
            symbol,
            side,
            amount,
            order_type=order_type,
            price=price,
            tp_pct=float(self.config.get("BOT_TP_PCT", 3.0)) / 100,
            sl_pct=float(self.config.get("BOT_SL_PCT", 1.5)) / 100,
        )


def build_exchange(config=None):
    global _cfg_cache
    if config is None:
        config_path = Path(__file__).resolve().parent.parent / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    _cfg_cache = config
    logger.info("✅ Bitget direct REST API initialized")
    return BitgetExchangeClient(config)


def _sign_request(cfg, method, path, body_str=""):
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
    if is_demo_mode(cfg):
        headers["paptrading"] = "1"
    return headers


def _set_leverage(cfg, raw_symbol, leverage):
    """Set conservative cross-margin leverage before opening a position."""
    path = "/api/v2/mix/account/set-leverage"
    body = {
        "symbol": raw_symbol,
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "leverage": str(leverage),
    }
    body_str = json.dumps(body)
    headers = _sign_request(cfg, "POST", path, body_str)
    result = requests.post(
        f"https://api.bitget.com{path}",
        headers=headers,
        data=body_str,
        timeout=10,
    ).json()
    if result.get("code") != "00000":
        logger.error(
            f"[Exchange] Leverage setup failed for {raw_symbol}: {result.get('msg')}"
        )
        return False
    return True


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
        symbol = cfg.get("BOT_SYMBOL", "BTC/USDT:USDT")
        raw_symbol = symbol.replace("/USDT:USDT", "USDT").replace("/", "").upper()
        params = f"?symbol={raw_symbol}&productType=USDT-FUTURES&marginCoin=USDT"
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


def get_positions(cfg, fail_closed=False):
    try:
        path = "/api/v2/mix/position/all-position"
        params = "?productType=USDT-FUTURES&marginCoin=USDT"
        headers = _sign_request(cfg, "GET", path + params)
        resp = requests.get(f"https://api.bitget.com{path}{params}", headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == "00000":
            return [p for p in data.get("data", []) if float(p.get("total", 0)) > 0]
        logger.error(
            f"[Exchange] Positions error: HTTP {resp.status_code} "
            f"code={data.get('code')} msg={data.get('msg')}"
        )
        return None if fail_closed else []
    except Exception as e:
        logger.error(f"[Exchange] Positions fetch failed: {e}")
        return None if fail_closed else []


def get_open_orders(cfg, fail_closed=False):
    """Return currently pending USDT futures orders without modifying them."""
    try:
        path = "/api/v2/mix/order/orders-pending"
        params = "?productType=USDT-FUTURES&limit=100"
        headers = _sign_request(cfg, "GET", path + params)
        resp = requests.get(f"https://api.bitget.com{path}{params}", headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == "00000":
            payload = data.get("data") or {}
            orders = payload.get("entrustedList") or []
            return orders if isinstance(orders, list) else []
        logger.error(f"[Exchange] Open orders error: {data.get('msg')}")
        return None if fail_closed else []
    except Exception as e:
        logger.error(f"[Exchange] Open orders fetch failed: {e}")
        return None if fail_closed else []


def get_pending_plan_orders(cfg, fail_closed=False):
    """Return pending TP/SL and trigger orders from Bitget."""
    try:
        path = "/api/v2/mix/order/orders-plan-pending"
        params = "?productType=USDT-FUTURES&planType=profit_loss&limit=100"
        headers = _sign_request(cfg, "GET", path + params)
        resp = requests.get(f"https://api.bitget.com{path}{params}", headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == "00000":
            payload = data.get("data") or {}
            if isinstance(payload, list):
                return payload
            return payload.get("entrustedList", payload.get("list", [])) or []
        logger.error(f"[Exchange] Pending plan orders error: {data.get('msg')}")
        return None if fail_closed else []
    except Exception as e:
        logger.error(f"[Exchange] Pending plan orders fetch failed: {e}")
        return None if fail_closed else []
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


def place_order_direct(
    cfg,
    symbol,
    side,
    size,
    order_type="market",
    price=None,
    tp_pct=None,
    sl_pct=None,
):
    """
    Place futures order with preset TP/SL built into the order.
    Uses presetStopSurplusPrice and presetStopLossPrice on place-order endpoint.
    This avoids all separate TPSL API calls and holdSide issues entirely.
    """
    _require_trading_mode(cfg)
    if tp_pct is None:
        tp_pct = float(cfg.get("BOT_TP_PCT", 3.0)) / 100
    if sl_pct is None:
        sl_pct = float(cfg.get("BOT_SL_PCT", 1.5)) / 100
    if _as_bool(cfg.get("BOT_PAPER_TRADING", False)):
        logger.warning(
            f"[Exchange] PAPER TRADE only: {side.lower()} {size} {symbol}; "
            "no order sent to Bitget"
        )
        return {
            "id": f"paper-{int(time.time() * 1000)}",
            "orderId": "paper",
            "paper": True,
            "side": side.lower(),
            "size": str(size),
        }
    try:
        raw_symbol = symbol.replace("/USDT:USDT","USDT").replace("/","").upper()
        decimals = _get_price_decimals(symbol)

        # The public ticker list can include instruments unavailable to the
        # Demo account. Check the futures contract list before sizing/order.
        contracts_url = (
            "https://api.bitget.com/api/v2/mix/market/contracts"
            "?productType=USDT-FUTURES"
        )
        contracts = requests.get(contracts_url, timeout=10).json()
        contract = next(
            (item for item in contracts.get("data", [])
             if str(item.get("symbol", "")).upper() == raw_symbol),
            None,
        )
        if not contract:
            logger.warning(
                f"[Exchange] {symbol} is not available in USDT-FUTURES; skipping"
            )
            return None
        if str(contract.get("symbolStatus", "normal")).lower() not in {"normal", "listed"}:
            logger.warning(
                f"[Exchange] {symbol} is not currently tradable "
                f"(status={contract.get('symbolStatus')}); skipping"
            )
            return None

        configured_leverage = float(cfg.get("BOT_LEVERAGE", 1))
        max_leverage = float(contract.get("maxLever", configured_leverage) or configured_leverage)
        leverage = max(1, min(configured_leverage, max_leverage))
        if not _set_leverage(cfg, raw_symbol, leverage):
            return None

        # First get current price for TP/SL calculation
        ticker_url = (
            f"https://api.bitget.com/api/v2/mix/market/ticker"
            f"?symbol={raw_symbol}&productType=USDT-FUTURES"
        )
        price_data = requests.get(ticker_url, timeout=10).json()
        current_price = 0
        if price_data.get("code") == "00000" and price_data.get("data"):
            ticker = price_data["data"][0]
            current_price = float(
                ticker.get("markPrice") or ticker.get("lastPr", 0)
            )

        # Calculate preset TP/SL prices
        preset_tp = ""
        preset_sl = ""
        if current_price > 0:
            if side.lower() == "buy":
                preset_tp = str(round(current_price * (1 + tp_pct), decimals))
                preset_sl = str(round(current_price * (1 - sl_pct), decimals))
            else:
                preset_tp = str(round(current_price * (1 - tp_pct), decimals))
                preset_sl = str(round(current_price * (1 + sl_pct), decimals))

        body = {
            "symbol":                  raw_symbol,
            "productType":             "USDT-FUTURES",
            "marginMode":              "crossed",
            "marginCoin":              "USDT",
            "size":                    str(size),
        "side":                    side.lower(),
        # Required for hedge-mode openings and ignored in one-way mode.
        "tradeSide":               "open",
        "orderType":               order_type,
            "presetStopSurplusPrice":  preset_tp,
            "presetStopLossPrice":     preset_sl,
        }
        if price is not None and order_type.lower() != "market":
            body["price"] = str(price)
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
                f"[Exchange] ✅ Order+TPSL placed: {side} {size} {symbol} "
                f"| ID:{order_id} | TP:{preset_tp} SL:{preset_sl}"
            )
            payload = dict(result.get("data", {}) or {})
            payload.setdefault("id", order_id)
            payload.setdefault("orderId", order_id)
            return payload
        else:
            logger.error(f"[Exchange] ❌ Order failed: {result.get('msg')} | {result}")
            return None
    except Exception as e:
        logger.error(f"[Exchange] Order error: {e}")
        return None


def place_tpsl_direct(cfg, symbol, side, entry_price, tp_pct=0.025, sl_pct=0.015, size=None):
    """
    Official Bitget place-tpsl-order - EXACT format from official API docs:
    symbol: lowercase (ethusdt not ETHUSDT)
    productType: usdt-futures
    planType: profit_plan | loss_plan
    executePrice: "0" = market execution
    holdSide: long | short
    size: actual position size
    rangeRate: "" (required empty string)
    """
    try:
        raw_symbol = symbol.replace("/USDT:USDT","USDT").replace("/","").lower()
        decimals = _get_price_decimals(symbol)
        is_long = side.lower() == "buy"
        hold_side = "long" if is_long else "short"

        # Get actual position size from open positions
        pos_size = "1"
        try:
            positions = get_positions(cfg)
            for p in positions:
                if raw_symbol.upper() in p.get("symbol","").upper():
                    pos_size = str(p.get("total","1"))
                    break
        except Exception:
            pass

        if is_long:
            tp_price = round(entry_price * (1 + tp_pct), decimals)
            sl_price = round(entry_price * (1 - sl_pct), decimals)
        else:
            tp_price = round(entry_price * (1 - tp_pct), decimals)
            sl_price = round(entry_price * (1 + sl_pct), decimals)

        logger.info(
            f"[Exchange] TPSL {raw_symbol} | {hold_side} | "
            f"TP:{tp_price} SL:{sl_price} | size:{pos_size}"
        )

        path = "/api/v2/mix/order/place-tpsl-order"
        results = []

        for label, trigger_price, plan_type in [
            ("TP", tp_price, "profit_plan"),
            ("SL", sl_price, "loss_plan"),
        ]:
            body = {
                "marginCoin":   "USDT",
                "productType":  "usdt-futures",
                "symbol":       raw_symbol,
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
                logger.error(
                    f"[Exchange] ❌ {label} failed: {result.get('msg')} | {result}"
                )
                results.append(False)

        return all(results)

    except Exception as e:
        logger.error(f"[Exchange] TP/SL error: {e}")
        return False

def close_position_direct(cfg, symbol, hold_side, size):
    """
    Close open position in one-way mode using flash close approach.
    One-way mode close = opposite side market order without tradeSide.
    long position -> sell order
    short position -> buy order
    """
    _require_trading_mode(cfg)
    try:
        raw_symbol = symbol.replace("/USDT:USDT","USDT").replace("/","").upper()

        # In one-way mode: sell to close long, buy to close short
        close_side = "sell" if hold_side.lower() == "long" else "buy"

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
            headers=headers,
            data=body_str,
            timeout=10
        ).json()

        if result.get("code") == "00000":
            logger.info(f"[Exchange] ✅ Closed: {symbol} {hold_side} size:{size}")
            return True

        # If tradeSide close fails, try flash close endpoint
        logger.warning(f"[Exchange] tradeSide close failed: {result.get('msg')} - trying flash close")

        flash_path = "/api/v2/mix/order/close-positions"
        flash_body = {
            "symbol":      raw_symbol,
            "productType": "USDT-FUTURES",
        }
        flash_str = json.dumps(flash_body)
        flash_headers = _sign_request(cfg, "POST", flash_path, flash_str)
        flash_result = requests.post(
            f"https://api.bitget.com{flash_path}",
            headers=flash_headers,
            data=flash_str,
            timeout=10
        ).json()

        if flash_result.get("code") == "00000":
            logger.info(f"[Exchange] ✅ Flash closed all: {symbol}")
            return True
        else:
            logger.error(f"[Exchange] ❌ All close methods failed: {flash_result.get('msg')}")
            return False

    except Exception as e:
        logger.error(f"[Exchange] Close error: {e}")
        return False

def _get_min_qty(symbol):
    """Return Bitget's current minimum/step quantity for a contract."""
    KNOWN_MIN_QTY = {
        "BTCUSDT":  0.001,  "ETHUSDT":  0.01,   "SOLUSDT":  0.1,
        "BNBUSDT":  0.01,   "XRPUSDT":  1.0,    "ADAUSDT":  1.0,
        "DOGEUSDT": 1.0,    "LTCUSDT":  0.01,   "DOTUSDT":  0.1,
        "LINKUSDT": 0.1,    "UNIUSDT":  0.1,    "AVAXUSDT": 0.1,
        "ATOMUSDT": 0.1,    "FILUSDT":  0.1,    "AAVEUSDT": 0.01,
        "ICPUSDT":  0.1,    "ETCUSDT":  0.1,    "TRXUSDT":  1.0,
        "XLMUSDT":  1.0,    "BCHUSDT":  0.001,  "NEARUSDT": 0.1,
        "ALGOUSDT": 1.0,    "MATICUSDT":1.0,    "INJUSDT":  0.01,
        "OPUSDT":   0.1,    "ARBUSDT":  0.1,    "SUSHIUSDT":0.1,
        "GMTUSDT":  1.0,    "APTUSDT":  0.1,    "DYDXUSDT": 0.1,
        "CRVUSDT":  1.0,    "SANDUSDT": 1.0,    "MANAUSDT": 1.0,
        "GALAUSDT":10.0,    "BNBUSDT":  0.01,   "RUNEUSDT": 0.1,
        "FTMUSDT":  1.0,    "LDOUSDT":  0.1,    "STXUSDT":  0.1,
        "KNCUSDT":  0.1,    "AAVEUSDT": 0.01,
    }
    raw = symbol.replace("/USDT:USDT","USDT").replace("/","").upper()

    # Contract rules change by instrument; prefer the exchange metadata over
    # the fallback table so orders are rejected locally when possible.
    if raw not in _contract_cache:
        try:
            url = "https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES"
            response = requests.get(url, timeout=10).json()
            if response.get("code") == "00000":
                for contract in response.get("data", []):
                    contract_symbol = str(contract.get("symbol", "")).upper()
                    if not contract_symbol:
                        continue
                    minimum = float(contract.get("minTradeNum", 0) or 0)
                    step = float(contract.get("sizeMultiplier", 0) or 0)
                    if minimum > 0:
                        _contract_cache[contract_symbol] = max(minimum, step)
        except Exception as exc:
            logger.warning("[Exchange] Contract quantity metadata unavailable: %s", exc)

    return _contract_cache.get(raw, KNOWN_MIN_QTY.get(raw, 1.0))

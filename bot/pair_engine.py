import math
import time
import logging
from bot.strategy         import HFScalperStrategy
from bot.bb_strategy      import BollingerStrategy
from bot.multi_strategy   import MultiStrategy
from bot.position_monitor import PositionMonitor
from bot.exchange_factory import build_exchange
from bot.market_scanner   import MarketScanner

logger = logging.getLogger(__name__)

PAIR_PRECISION = {
    "DOGE/USDT:USDT": 1,
    "XRP/USDT:USDT":  1,
    "PEPE/USDT:USDT": 1000,
    "DEFAULT":        1,
}

MIN_COST = 5.5  # Bitget minimum $5

class PairTrader:
    def __init__(self, symbol, config, exchange):
        self.symbol   = symbol
        self.config   = config
        self.exchange = exchange
        self.precision = PAIR_PRECISION.get(symbol, 1)

        pair_cfg = dict(config)
        pair_cfg["BOT_SYMBOL"] = symbol

        ema = HFScalperStrategy(pair_cfg)
        bb  = BollingerStrategy(pair_cfg)
        self.strategy = MultiStrategy(pair_cfg, ema, bb)
        self.monitor  = PositionMonitor(pair_cfg, None)
        self.monitor.exchange = exchange
        self.monitor.symbol   = symbol
        self.monitor.tp_pct   = float(config.get("BOT_TP_PCT", "3.0")) / 100
        self.monitor.sl_pct   = float(config.get("BOT_SL_PCT", "1.2")) / 100
        logger.info(f"[PairTrader] {symbol} ready")

    def _get_total_balance(self):
        try:
            bal   = __import__("bot.exchange_factory", fromlist=["get_balance"]).get_balance(self.config)
            free  = float(bal.get("USDT", {}).get("free",  0) or 0)
            used  = float(bal.get("USDT", {}).get("used",  0) or 0)
            total = free + used
            return total if total > 1 else 6.0
        except:
            return 6.0

    def _calc_qty(self, price):
        if not price or float(price) == 0:
            from bot.exchange_factory import fetch_ohlcv_direct
            _c = fetch_ohlcv_direct(self.symbol, "1m", limit=1)
            price = float(_c[-1][4]) if _c else 0
        if not price or float(price) == 0:
            logger.warning(f"[PairTrader] {self.symbol} price=0, skipping qty calc")
            return 0
        total     = self._get_total_balance()
        risk_usd  = min(total * 0.30, 7.0)
        risk_usd  = max(risk_usd, MIN_COST)
        raw_qty   = risk_usd / float(price)
        qty = math.ceil(raw_qty / self.precision) * self.precision
        if qty * float(price) < MIN_COST:
            qty += self.precision
        return qty

    def monitor_existing(self):
        """Only monitors — does not open new trades."""
        try:
            self.monitor.check_and_close()
        except Exception as e:
            logger.error(f"[PairTrader] {self.symbol} monitor error: {e}")

    def trade(self):
        """Attempt to open a new trade on this pair."""
        try:
            # Check cooldown period
            if not self._can_trade_symbol(self.symbol):
                return False
                
            sig = self.strategy.generate_signal(self.exchange)
            if not sig or sig.direction == "FLAT":
                logger.info(f"[PairTrader] {self.symbol} signal=FLAT - skip")
                return False

            side = "buy" if sig.direction == "LONG" else "sell"
            qty  = self._calc_qty(sig.price)
            if not qty or qty == 0:
                logger.warning(f"[PairTrader] {self.symbol} qty=0, skipping trade")
                return False

            # Calculate TP/SL prices
            tp_pct = float(self.config.get("BOT_TP_PCT", "3.0")) / 100
            sl_pct = float(self.config.get("BOT_SL_PCT", "1.2")) / 100
            try:
                from bot.exchange_factory import fetch_ohlcv_direct
                _c = fetch_ohlcv_direct(self.symbol, "1m", limit=1)
                mark_price = float(_c[-1][4]) if _c else float(sig.price)
            except Exception:
                mark_price = float(sig.price)

            if side == "buy":
                tp_price = round(mark_price * (1 + tp_pct), 6)
                sl_price = round(mark_price * (1 - sl_pct), 6)
            else:
                tp_price = round(mark_price * (1 - tp_pct), 6)
                sl_price = round(mark_price * (1 + sl_pct), 6)

            logger.info(f"[PairTrader] {self.symbol} placing {side} {qty} TP={tp_price} SL={sl_price}")
            # Use direct REST API instead of ccxt (PythonAnywhere compatible)
            from bot.exchange_factory import place_order_direct
            order_result = place_order_direct(
                cfg=self.config,
                symbol=self.symbol,
                side=side,
                size=qty,
                order_type="market"
            )
            # Create a mock order object for logging compatibility
            order = {
                'id': order_result.get('data', {}).get('orderId', 'N/A'),
                'info': order_result
            }
            # Check if order failed
            if order_result.get('code') != '00000':
                logger.error(f"[PairTrader] {self.symbol} order failed: {order_result}")
                return False
            logger.info(
                f"[PairTrader] {self.symbol} ORDER FILLED! "
                f"id={order.get('id')} qty={qty} side={side}"
            )
            return True

        except Exception as e:
            logger.error(f"[PairTrader] {self.symbol} trade error: {e}")
            return False
class PairEngine:
    def __init__(self, config):
        self.config   = config
        self.exchange = build_exchange(config)
        # DISABLED - causes spot API call: self.exchange.load_markets()
        self.scanner  = MarketScanner(config, self.exchange)
        self.traders  = {}  # symbol -> PairTrader cache
        self.max_open = 3   # HARD LIMIT
        logger.info("[PairEngine] Ready — Smart Market Scanner active")

    
    def _can_trade_symbol(self, symbol):
        """Check if symbol is in cooldown period"""
        import time
        if symbol in self.last_trade_time:
            minutes_since = (time.time() - self.last_trade_time[symbol]) / 60
            if minutes_since < self.cooldown_minutes:
                remaining = int(self.cooldown_minutes - minutes_since)
                logger.info("[PairEngine] {} in cooldown ({}m remaining)".format(symbol, remaining))                return False
        return True

    def _record_trade(self, symbol):
        """Record trade time for cooldown"""
        import time
        self.last_trade_time[symbol] = time.time()

def _get_trader(self, symbol):
        """Get or create a PairTrader for a symbol."""
        # Handle both dict and string symbols
        if isinstance(symbol, dict):
            symbol_str = symbol.get('symbol', str(symbol))
        else:
            symbol_str = str(symbol)
        
        if symbol_str not in self.traders:
            self.traders[symbol_str] = PairTrader(symbol_str, self.config, self.exchange)
        return self.traders[symbol_str]

    def _count_open(self):
        try:
            positions = __import__("bot.exchange_factory", fromlist=["get_positions"]).get_positions(self.config)
            return sum(
                1 for p in positions
                if float(p.get("contracts", 0) or 0) > 0
            )
        except:
            return 0

    def tick_all(self):
        # Step 1: Get top 3 pairs from scanner
        top_pairs = self.scanner.get_top_pairs()
        logger.info(f"[PairEngine] Top pairs this hour: {top_pairs}")

        # Step 2: Monitor ALL existing open positions first
        # (including any pair not in current top 3)
        try:
            all_positions = __import__("bot.exchange_factory", fromlist=["get_positions"]).get_positions(self.config)
            open_symbols  = [
                p.get("symbol") for p in all_positions
                if float(p.get("contracts", 0) or 0) > 0
            ]
            for sym in open_symbols:
                logger.info(f"[PairEngine] Monitoring existing: {sym}")
                trader = self._get_trader(sym)
                trader.monitor_existing()
                time.sleep(1)
        except Exception as e:
            logger.error(f"[PairEngine] Monitor sweep error: {e}")

        # Step 3: Count open positions
        open_count = self._count_open()
        logger.info(
            f"[PairEngine] Open positions: {open_count}/{self.max_open}"
        )

        # HARD LIMIT CHECK
        if open_count >= self.max_open:
            logger.info(
                f"[PairEngine] MAX TRADES REACHED ({open_count}) "
                f"— no new entries until one closes"
            )
            return

        # Step 4: Try to open trades on available top pairs
        available_slots = self.max_open - open_count
        available_pairs = self.scanner.get_available_pairs()

        logger.info(
            f"[PairEngine] {available_slots} slot(s) free | "
            f"Candidates: {available_pairs}"
        )

        trades_opened = 0
        for symbol in available_pairs:
            if trades_opened >= available_slots:
                break
            logger.info(f"[PairEngine] --- Attempting {symbol} ---")
            trader = self._get_trader(symbol)
            opened = trader.trade()
            if opened:
                trades_opened += 1
                open_count += 1
                time.sleep(2)
            # Re-check hard limit
            if open_count >= self.max_open:
                logger.info("[PairEngine] Hard limit reached — stopping")
                break

    def get_status(self):
        return {
            "top_pairs":    self.scanner.top_pairs,
            "open_count":   self._count_open(),
            "max_trades":   self.max_open,
            "last_scan":    self.scanner.last_scan_time,
            "scores":       {
                k: v["score"]
                for k, v in list(self.scanner.scores.items())[:10]
            }
        }

import math
import logging
from bot.exchange_factory import build_exchange

logger = logging.getLogger(__name__)


class TradeRecord:
    def __init__(self, direction, price, qty, symbol):
        self.direction = direction
        self.price     = price
        self.qty       = qty
        self.symbol    = symbol

    def __repr__(self):
        return f"TradeRecord({self.direction} {self.qty} {self.symbol} @ {self.price})"


class RiskManager:
    def __init__(self, config):
        self.config         = config
        self.exchange       = build_exchange(config)
        self.symbol         = config.get('BOT_SYMBOL',             'DOGE/USDT:USDT')
        self.risk_pct       = float(config.get('BOT_RISK_PCT',     '30.0')) / 100
        self.sl_pct         = float(config.get('BOT_SL_PCT',       '1.0'))  / 100
        self.tp_pct         = float(config.get('BOT_TP_PCT',       '2.0'))  / 100
        self.max_pos_usd    = float(config.get('BOT_MAX_POS_USD',  '6.0'))
        self.min_order_usd  = 5.5   # Bitget hard minimum is $5 — we use $5.50 for safety
        self.max_daily_loss = float(config.get('BOT_MAX_DAILY_LOSS_USD', '2.0'))
        self.max_errors     = int(config.get('BOT_MAX_ERRORS',     '50'))
        self.error_count    = 0
        self.daily_loss     = 0.0
        self.halted         = False
        logger.info(f"[Risk] Ready | {self.symbol} | risk={self.risk_pct*100}% | max_pos=${self.max_pos_usd}")

    def is_halted(self):
        return self.halted

    def reset(self):
        self.halted      = False
        self.error_count = 0
        self.daily_loss  = 0.0
        logger.info("[Risk] Reset")

    def register_error(self, exc):
        self.error_count += 1
        logger.warning(f"[Risk] Error #{self.error_count}: {exc}")
        if self.error_count >= self.max_errors:
            self.halted = True
            logger.critical(f"[Risk] {self.error_count} errors — halting")

    def _has_open_position(self):
        """Check if there is already an open position — if so, skip new orders."""
        try:
            positions = __import__("bot.exchange_factory", fromlist=["get_positions"]).get_positions(self.config)
            for p in positions:
                size = float(p.get('contracts', 0) or 0)
                if size > 0:
                    side = p.get('side','')
                    logger.info(f"[Risk] Open position exists: {side} {size} — skipping new order")
                    return True
            return False
        except Exception as e:
            logger.warning(f"[Risk] Position check error: {e}")
            return False

    def _get_balance(self):
        """Fetch USDT balance including margin in use."""
        try:
            bal = __import__("bot.exchange_factory", fromlist=["get_balance"]).get_balance(self.config)

            # Method 1: free USDT
            free = float(bal.get('USDT', {}).get('free', 0) or 0)
            used = float(bal.get('USDT', {}).get('used', 0) or 0)
            total = free + used  # total = free + margin in use

            if total > 0.01:
                logger.info(f"[Risk] Balance: free=${free:.4f} + margin=${used:.4f} = total=${total:.4f}")
                # If free is too low but we have margin, use total as reference
                if free < 1.0 and total > 1.0:
                    logger.info(f"[Risk] Using total balance ${total:.4f} as reference")
                    return total
                return total

            # Method 2: Bitget info data
            for item in bal.get('info', {}).get('data', []):
                if isinstance(item, dict):
                    coin = item.get('marginCoin','') or item.get('coin','')
                    if coin == 'USDT':
                        equity = item.get('equity', 0) or item.get('accountEquity', 0)
                        if equity and float(equity) > 0:
                            logger.info(f"[Risk] Balance (equity): ${equity}")
                            return float(equity)

            logger.warning(f"[Risk] Balance unreadable — fallback $5.59")
            return 5.59

        except Exception as e:
            logger.error(f"[Risk] Balance error: {e} — fallback $5.59")
            return 5.59

    def _calc_qty(self, price):
        """Calculate order quantity ensuring minimum $5.50 order value."""
        balance  = self._get_balance()
        risk_usd = min(balance * self.risk_pct, self.max_pos_usd)

        # CRITICAL: enforce Bitget $5 minimum
        risk_usd = max(risk_usd, self.min_order_usd)

        raw_qty = risk_usd / float(price)

        # Round UP to whole number (DOGE requires integer quantities)
        qty = math.ceil(raw_qty)

        # Double-check value
        order_value = qty * float(price)
        if order_value < self.min_order_usd:
            qty = math.ceil(self.min_order_usd / float(price)) + 1

        logger.info(f"[Risk] balance=${balance:.2f} risk_usd=${risk_usd:.2f} qty={qty} value=${qty*float(price):.2f}")
        return qty

    def place_order(self, direction, price):
        if self.halted:
            logger.warning("[Risk] Halted — skipping")
            return None

        # CRITICAL: Do not open new position if one already exists
        if self._has_open_position():
            logger.info("[Risk] Position already open — waiting for it to close before new order")
            return None

        if self.daily_loss >= self.max_daily_loss:
            logger.warning(f"[Risk] Daily loss limit hit ${self.daily_loss:.2f}")
            self.halted = True
            return None

        try:
            qty  = self._calc_qty(price)
            side = 'buy' if direction == 'LONG' else 'sell'

            logger.info(f"[Risk] Placing {side} {qty} {self.symbol} @ market (~${qty*float(price):.2f})")

            order = self.exchange.create_order(
                symbol = self.symbol,
                type   = 'market',
                side   = side,
                amount = qty,
                params = {"tdMode": "cross", "marginCoin": "USDT", "productType": "USDT-FUTURES"}
            )

            logger.info(f"[Risk] ✅ ORDER FILLED! id={order.get('id')} qty={qty} side={side}")
            self.error_count = 0
            return TradeRecord(direction, price, qty, self.symbol)

        except Exception as e:
            self.error_count += 1
            logger.warning(f"[Risk] Error #{self.error_count}: {e}")
            logger.error(f"[Risk] Exchange error placing order: {e}")
            if self.error_count >= self.max_errors:
                self.halted = True
                logger.critical(f"[Risk] Too many errors — halting")
            return None

    def execute_signal(self, exchange, sig):
        direction = sig.get('direction') if isinstance(sig, dict) else getattr(sig, 'direction', None)
        price     = sig.get('price')     if isinstance(sig, dict) else getattr(sig, 'price', None)

        if not direction or direction == 'FLAT':
            return None
        if self.halted:
            logger.warning("[Risk] Halted — skipping execute_signal")
            return None

        return self.place_order(direction, price)

    def log_trade_result(self, direction, entry, exit_price, qty, reason):
        import json
        from datetime import datetime
        pnl = (exit_price - entry) * qty if direction == 'LONG' else (entry - exit_price) * qty
        record = {
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "entry":     entry,
            "exit":      exit_price,
            "qty":       qty,
            "pnl":       round(pnl, 4),
            "reason":    reason
        }
        journal_file = "/home/macbere/trading_bot/logs/trade_journal.json"
        try:
            with open(journal_file, "r") as f:
                journal = json.load(f)
        except:
            journal = []
        journal.append(record)
        with open(journal_file, "w") as f:
            json.dump(journal, f, indent=2)
        logger.info(f"[Journal] Trade logged: {direction} PnL=${pnl:.4f} reason={reason}")
        return pnl

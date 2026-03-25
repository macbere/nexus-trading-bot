"""
Position Monitor - Trailing Stop & Trade Logger
Runs as background thread. NEVER closes losing positions.
Only locks in profits via trailing stops.
"""
import time
import json
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class PositionMonitor:
    def __init__(self, config):
        self.config = config
        self.running = False
        self.thread = None
        self.trade_log_file = "logs/trade_log.json"
        self.monitored = {}  # symbol -> {entry, trail_level}
        self._ensure_log_file()

    def _ensure_log_file(self):
        import os
        os.makedirs("logs", exist_ok=True)
        if not os.path.exists(self.trade_log_file):
            with open(self.trade_log_file, "w") as f:
                json.dump([], f)

    def start(self):
        """Start monitor as background thread"""
        self.running = True
        self.thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self.thread.start()
        logger.info("[Monitor] Position monitor started")

    def stop(self):
        self.running = False
        logger.info("[Monitor] Position monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop - runs every 60 seconds"""
        while self.running:
            try:
                self._check_positions()
            except Exception as e:
                logger.error(f"[Monitor] Loop error: {e}")
            time.sleep(60)

    def _check_positions(self):
        """Check all open positions and apply trailing stops"""
        try:
            from bot.exchange_factory import get_positions, _sign_request
            import requests

            positions = get_positions(self.config)

            if not positions:
                logger.info("[Monitor] No open positions")
                return

            for p in positions:
                symbol = p.get("symbol", "")
                hold_side = p.get("holdSide", "long")
                size = float(p.get("total", 0))
                entry = float(p.get("openPriceAvg", 0))
                mark = float(p.get("markPrice", 0))
                margin = float(p.get("margin", 0))
                pnl = float(p.get("unrealizedPL", 0))

                if size <= 0 or entry <= 0 or margin <= 0:
                    continue

                # Calculate ROE accurately
                roe_pct = (pnl / margin) * 100

                logger.info(
                    f"[Monitor] {symbol} | {hold_side.upper()} | "
                    f"PnL:{pnl:.4f} | ROE:{roe_pct:.2f}%"
                )

                # Initialize tracking
                if symbol not in self.monitored:
                    self.monitored[symbol] = {
                        "entry": entry,
                        "trail_level": 0,
                        "opened_at": datetime.now().isoformat()
                    }

                trail = self.monitored[symbol]["trail_level"]

                # TRAILING STOP LOGIC
                # Level 0 -> Level 1: Position reaches +1.5% ROE
                # Action: Move SL to breakeven (0%)
                if roe_pct >= 1.5 and trail < 1:
                    new_sl = entry * 1.001  # Slightly above breakeven
                    success = self._update_sl(symbol, hold_side, new_sl)
                    if success:
                        self.monitored[symbol]["trail_level"] = 1
                        logger.info(
                            f"[Monitor] 🔒 {symbol} SL moved to "
                            f"BREAKEVEN @ {new_sl:.6f} (ROE:{roe_pct:.2f}%)"
                        )

                # Level 1 -> Level 2: Position reaches +2.5% ROE
                # Action: Move SL to +1% locked profit
                elif roe_pct >= 2.5 and trail < 2:
                    if hold_side == "long":
                        new_sl = entry * 1.01
                    else:
                        new_sl = entry * 0.99
                    success = self._update_sl(symbol, hold_side, new_sl)
                    if success:
                        self.monitored[symbol]["trail_level"] = 2
                        logger.info(
                            f"[Monitor] 🔒 {symbol} SL moved to "
                            f"+1% PROFIT @ {new_sl:.6f} (ROE:{roe_pct:.2f}%)"
                        )

                # Level 2 -> Level 3: Position reaches +4% ROE
                # Action: Move SL to +2% - let big winners run
                elif roe_pct >= 4.0 and trail < 3:
                    if hold_side == "long":
                        new_sl = entry * 1.02
                    else:
                        new_sl = entry * 0.98
                    success = self._update_sl(symbol, hold_side, new_sl)
                    if success:
                        self.monitored[symbol]["trail_level"] = 3
                        logger.info(
                            f"[Monitor] 🚀 {symbol} SL moved to "
                            f"+2% PROFIT @ {new_sl:.6f} (ROE:{roe_pct:.2f}%)"
                        )

        except Exception as e:
            logger.error(f"[Monitor] Check error: {e}")

    def _update_sl(self, symbol, hold_side, new_sl_price):
        """Update stop loss on Bitget"""
        try:
            from bot.exchange_factory import _sign_request
            import requests

            raw_symbol = symbol.replace("USDT", "") + "USDT"
            # Remove any extra USDT
            raw_symbol = raw_symbol.replace("USDTUSDT", "USDT")

            path = "/api/v2/mix/order/place-tpsl-order"
            body = {
                "symbol": raw_symbol,
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "planType": "pos_loss",
                "triggerPrice": str(round(new_sl_price, 6)),
                "triggerType": "mark_price",
                "executePrice": "0",
                "holdSide": hold_side,
            }
            body_str = json.dumps(body)
            headers = _sign_request(self.config, "POST", path, body_str)
            resp = requests.post(
                f"https://api.bitget.com{path}",
                headers=headers,
                data=body_str,
                timeout=10
            )
            result = resp.json()
            if result.get("code") == "00000":
                return True
            else:
                logger.error(
                    f"[Monitor] SL update failed: {result.get('msg')}"
                )
                return False
        except Exception as e:
            logger.error(f"[Monitor] SL update error: {e}")
            return False

    def log_trade(self, symbol, side, entry_price, qty, score):
        """Log a new trade entry"""
        try:
            with open(self.trade_log_file, "r") as f:
                trades = json.load(f)

            trade = {
                "id": len(trades) + 1,
                "symbol": symbol,
                "side": side,
                "entry_price": entry_price,
                "qty": qty,
                "score": score,
                "opened_at": datetime.now().isoformat(),
                "closed_at": None,
                "exit_price": None,
                "pnl": None,
                "result": None
            }
            trades.append(trade)

            with open(self.trade_log_file, "w") as f:
                json.dump(trades, f, indent=2)

            logger.info(f"[Monitor] Trade #{trade['id']} logged: {symbol}")
        except Exception as e:
            logger.error(f"[Monitor] Trade log error: {e}")

    def get_win_rate(self):
        """Calculate win rate from trade history"""
        try:
            with open(self.trade_log_file, "r") as f:
                trades = json.load(f)

            closed = [t for t in trades if t.get("result")]
            if not closed:
                return None

            wins = sum(1 for t in closed if t.get("result") == "win")
            win_rate = (wins / len(closed)) * 100
            return {
                "total_trades": len(closed),
                "wins": wins,
                "losses": len(closed) - wins,
                "win_rate": round(win_rate, 1)
            }
        except Exception:
            return None

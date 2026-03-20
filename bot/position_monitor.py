import logging
from bot.exchange_factory import get_positions, get_balance, _cfg_cache
import time
from bot.exchange_factory import build_exchange

logger = logging.getLogger(__name__)

ROE_OPTIONS = [20, 25, 30, 35, 40, 45, 50, 70, 80, 100]

class PositionMonitor:

    def _direct_get_positions(self):
        """Get positions via direct API - bypasses ccxt auth"""
        try:
            from bot.exchange_factory import get_positions, _cfg_cache
            if _cfg_cache:
                raw = get_positions(_cfg_cache)
                result = []
                for p in raw:
                    result.append({
                        "symbol":        p["symbol"],
                        "side":          p["side"],
                        "contracts":     p["size"],
                        "entryPrice":    p["entry"],
                        "markPrice":     p["mark"],
                        "unrealizedPnl": p["pnl"],
                        "percentage":    p["roe"],
                        "info":          p["raw"],
                    })
                return result
        except Exception as e:
            logger.error(f"[Monitor] direct positions error: {e}")
        # Fallback
        try:
            positions = self._direct_get_positions()
            return [p for p in positions if float(p.get("contracts", 0) or 0) > 0]
        except Exception as e2:
            logger.error(f"[Monitor] fallback positions error: {e2}")
            return []

    def __init__(self, config, risk_manager):
        self.config       = config
        self.risk         = risk_manager
        self.exchange     = build_exchange(config)
        self.symbol       = config.get("BOT_SYMBOL", "DOGE/USDT:USDT")
        self.target_roe   = float(config.get("BOT_TARGET_ROE", "25"))
        self.sl_roe       = float(config.get("BOT_SL_ROE",     "10"))
        # Keep price-based as fallback
        self.tp_pct       = float(config.get("BOT_TP_PCT", "3.0")) / 100
        self.sl_pct       = float(config.get("BOT_SL_PCT", "1.2")) / 100
        logger.info(
            f"[Monitor] Ready | ROE_TP=+{self.target_roe}% "
            f"ROE_SL=-{self.sl_roe}% | symbol={self.symbol}"
        )

    def _reload_roe(self):
        """Reload ROE target from config on every check (allows live changes)."""
        try:
            import json
            with open("/home/macbere/trading_bot/config.json", "r") as f:
                cfg = json.load(f)
            self.target_roe = float(cfg.get("BOT_TARGET_ROE", self.target_roe))
            self.sl_roe     = float(cfg.get("BOT_SL_ROE",     self.sl_roe))
        except:
            pass

    def _get_positions(self):
        return self._direct_get_positions()

    
    def _calc_roe(self, position):
        """
        ROE = (unrealized PnL / initial margin) * 100
        This is what Bitget shows as ROE% in the app.
        """
        try:
            pnl    = float(position.get("unrealizedPnl", 0) or 0)
            margin = float(position.get("initialMargin",  0) or 0)
            if margin <= 0:
                # Fallback: calculate from entry/mark
                side   = position.get("side", "long")
                entry  = float(position.get("entryPrice", 0) or 0)
                mark   = float(position.get("markPrice",  entry) or entry)
                size   = float(position.get("contracts",  0) or 0)
                if entry > 0:
                    if side == "long":
                        pnl = (mark - entry) * size
                    else:
                        pnl = (entry - mark) * size
                    margin = entry * size * 0.1  # assume 10x leverage
            if margin > 0:
                roe = (pnl / margin) * 100
                return round(roe, 2), round(pnl, 4)
            return 0.0, 0.0
        except Exception as e:
            logger.warning(f"[Monitor] ROE calc error: {e}")
            return 0.0, 0.0

    def _close_position(self, position, reason):
        try:
            side       = position.get("side")
            size       = float(position.get("contracts", 0))
            close_side = "sell" if side == "long" else "buy"
            entry      = float(position.get("entryPrice", 0) or 0)
            mark       = float(position.get("markPrice",  entry) or entry)

            logger.info(f"[Monitor] CLOSING {side} {size} {self.symbol} — {reason}")

            order = self.exchange.create_order(
                symbol = self.symbol,
                type   = "market",
                side   = close_side,
                amount = size,
                params = {"reduceOnly": True, "tdMode": "cross", "marginCoin": "USDT", "productType": "USDT-FUTURES"}
            )

            roe, pnl = self._calc_roe(position)
            logger.info(
                f"[Monitor] CLOSED! side={side} entry={entry} "
                f"mark={mark} ROE={roe}% PnL=${pnl} reason={reason}"
            )

            # Log to trade journal
            try:
                if self.risk:
                    self.risk.log_trade_result(
                        direction  = side.upper(),
                        entry      = entry,
                        exit_price = mark,
                        qty        = size,
                        reason     = reason
                    )
            except Exception as je:
                logger.warning(f"[Monitor] Journal error: {je}")

            return True

        except Exception as e:
            logger.error(f"[Monitor] Close error: {e}")
            return False

    def check_and_close(self):
        """Main method — checks ROE on all open positions."""
        self._reload_roe()  # Always use latest config
        positions = self._get_positions()

        if not positions:
            return

        for pos in positions:
            roe, pnl = self._calc_roe(pos)
            side     = pos.get("side", "?")
            size     = float(pos.get("contracts", 0))

            logger.info(
                f"[Monitor] {self.symbol} {side.upper()} {size} | "
                f"ROE={roe:+.2f}% PnL=${pnl:+.4f} | "
                f"Target=+{self.target_roe}% SL=-{self.sl_roe}%"
            )

            # TAKE PROFIT — ROE hit target
            if roe >= self.target_roe:
                logger.info(
                    f"[Monitor] TAKE PROFIT HIT! "
                    f"ROE {roe:+.2f}% >= +{self.target_roe}%"
                )
                self._close_position(pos, f"TAKE_PROFIT_ROE_{self.target_roe}%")

            # STOP LOSS — ROE hit negative target
            elif roe <= -self.sl_roe:
                logger.info(
                    f"[Monitor] STOP LOSS HIT! "
                    f"ROE {roe:+.2f}% <= -{self.sl_roe}%"
                )
                self._close_position(pos, f"STOP_LOSS_ROE_{self.sl_roe}%")

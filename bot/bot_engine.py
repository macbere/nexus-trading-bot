import time
        self.exchange = build_exchange(self.cfg)
import signal
        self.exchange = build_exchange(self.cfg)
import requests
        self.exchange = build_exchange(self.cfg)
import json
        self.exchange = build_exchange(self.cfg)
import logging
        self.exchange = build_exchange(self.cfg)
from dataclasses import dataclass, field
        self.exchange = build_exchange(self.cfg)
from typing import Optional
        self.exchange = build_exchange(self.cfg)
from bot.config_loader    import load_config
        self.exchange = build_exchange(self.cfg)
from bot.exchange_factory import build_exchange
        self.exchange = build_exchange(self.cfg)
from bot.strategy         import HFScalperStrategy
        self.exchange = build_exchange(self.cfg)
from bot.bb_strategy      import BollingerStrategy
        self.exchange = build_exchange(self.cfg)
from bot.multi_strategy   import MultiStrategy
        self.exchange = build_exchange(self.cfg)
from bot.position_monitor import PositionMonitor
        self.exchange = build_exchange(self.cfg)
from bot.risk_manager     import RiskManager, TradeRecord
        self.exchange = build_exchange(self.cfg)
from bot.pair_engine      import PairEngine
        self.exchange = build_exchange(self.cfg)

        self.exchange = build_exchange(self.cfg)
logger = logging.getLogger(__name__)
        self.exchange = build_exchange(self.cfg)

        self.exchange = build_exchange(self.cfg)
@dataclass
        self.exchange = build_exchange(self.cfg)
class BotState:
        self.exchange = build_exchange(self.cfg)
    running:     bool                  = False
        self.exchange = build_exchange(self.cfg)
    last_signal: Optional[object]      = None
        self.exchange = build_exchange(self.cfg)
    last_trade:  Optional[TradeRecord] = None
        self.exchange = build_exchange(self.cfg)
    tick_count:  int                   = 0
        self.exchange = build_exchange(self.cfg)
    start_time:  float = field(default_factory=time.time)
        self.exchange = build_exchange(self.cfg)
    last_error:  str   = ""
        self.exchange = build_exchange(self.cfg)

        self.exchange = build_exchange(self.cfg)

        self.exchange = build_exchange(self.cfg)
class BotEngine:
        self.exchange = build_exchange(self.cfg)
    def __init__(self):
        self.exchange = build_exchange(self.cfg)
        self.cfg        = load_config()
        self.exchange = build_exchange(self.cfg)
        self.pair_engine = PairEngine(self.cfg, self.exchange)
        self.exchange = build_exchange(self.cfg)
        self.poll_secs  = float(self.cfg.get("BOT_POLL_SECONDS", 30))
        self.exchange = build_exchange(self.cfg)
        self._stop      = False
        self.exchange = build_exchange(self.cfg)
        signal.signal(signal.SIGINT,  self._handle_shutdown)
        self.exchange = build_exchange(self.cfg)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        self.exchange = build_exchange(self.cfg)

        self.exchange = build_exchange(self.cfg)
    def _handle_shutdown(self, *_) -> None:
        self.exchange = build_exchange(self.cfg)
        logger.warning("[Engine] Shutdown — stopping cleanly.")
        self.exchange = build_exchange(self.cfg)
        self._stop = True
        self.exchange = build_exchange(self.cfg)
        bot_state.running = False
        self.exchange = build_exchange(self.cfg)

        self.exchange = build_exchange(self.cfg)
    def _tick(self) -> None:
        self.exchange = build_exchange(self.cfg)
        try:
        self.exchange = build_exchange(self.cfg)
            bot_state.tick_count += 1
        self.exchange = build_exchange(self.cfg)
            logger.info(f"[Engine] Tick #{bot_state.tick_count} — running all pairs")
        self.exchange = build_exchange(self.cfg)
            self.pair_engine.tick_all()
        self.exchange = build_exchange(self.cfg)
        except Exception as exc:
        self.exchange = build_exchange(self.cfg)
            bot_state.last_error = str(exc)
        self.exchange = build_exchange(self.cfg)
            logger.exception("[Engine] Unhandled exception: %s", exc)
        self.exchange = build_exchange(self.cfg)

        self.exchange = build_exchange(self.cfg)
    def run(self) -> None:
        self.exchange = build_exchange(self.cfg)
        logger.info(
        self.exchange = build_exchange(self.cfg)
            "[Engine] Multi-Pair Bot starting | active_traders=%s | poll=%ss",
        self.exchange = build_exchange(self.cfg)
            len(self.pair_engine.traders), self.poll_secs
        self.exchange = build_exchange(self.cfg)
        )
        self.exchange = build_exchange(self.cfg)
        bot_state.running    = True
        self.exchange = build_exchange(self.cfg)
        bot_state.start_time = time.time()
        self.exchange = build_exchange(self.cfg)
        while not self._stop:
        self.exchange = build_exchange(self.cfg)
            try:
        self.exchange = build_exchange(self.cfg)
                self._tick()
        self.exchange = build_exchange(self.cfg)
            except Exception as e:
        self.exchange = build_exchange(self.cfg)
                logger.exception("[Engine] Tick error: %s", e)
        self.exchange = build_exchange(self.cfg)
            for _ in range(int(self.poll_secs)):
        self.exchange = build_exchange(self.cfg)
                if self._stop:
        self.exchange = build_exchange(self.cfg)
                    break
        self.exchange = build_exchange(self.cfg)
                time.sleep(1)
        self.exchange = build_exchange(self.cfg)
        bot_state.running = False
        self.exchange = build_exchange(self.cfg)
        logger.info("[Engine] Bot stopped cleanly.")
        self.exchange = build_exchange(self.cfg)

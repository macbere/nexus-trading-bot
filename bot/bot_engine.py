import time
import signal
import requests
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from bot.config_loader    import load_config
from bot.exchange_factory import build_exchange
from bot.strategy         import HFScalperStrategy
from bot.bb_strategy      import BollingerStrategy
from bot.multi_strategy   import MultiStrategy
from bot.position_monitor import PositionMonitor
from bot.risk_manager     import RiskManager, TradeRecord
from bot.pair_engine      import PairEngine

logger = logging.getLogger(__name__)

@dataclass
class BotState:
    running:     bool                  = False
    last_signal: Optional[object]      = None
    last_trade:  Optional[TradeRecord] = None
    tick_count:  int                   = 0
    start_time:  float = field(default_factory=time.time)
    last_error:  str   = ""

bot_state = BotState()

        self.exchange = build_exchange(self.cfg)
class BotEngine:
    def __init__(self):
        self.cfg        = load_config()
        self.pair_engine = PairEngine(self.cfg, self.exchange)
        self.poll_secs  = float(self.cfg.get("BOT_POLL_SECONDS", 30))
        self._stop      = False
        signal.signal(signal.SIGINT,  self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, *_) -> None:
        logger.warning("[Engine] Shutdown — stopping cleanly.")
        self._stop = True
        bot_state.running = False

    def _tick(self) -> None:
        try:
            bot_state.tick_count += 1
            logger.info(f"[Engine] Tick #{bot_state.tick_count} — running all pairs")
            self.pair_engine.tick_all()
        except Exception as exc:
            bot_state.last_error = str(exc)
            logger.exception("[Engine] Unhandled exception: %s", exc)

    def run(self) -> None:
        logger.info(
            "[Engine] Multi-Pair Bot starting | active_traders=%s | poll=%ss",
            len(self.pair_engine.traders), self.poll_secs
        )
        bot_state.running    = True
        bot_state.start_time = time.time()
        while not self._stop:
            try:
                self._tick()
            except Exception as e:
                logger.exception("[Engine] Tick error: %s", e)
            for _ in range(int(self.poll_secs)):
                if self._stop:
                    break
                time.sleep(1)
        bot_state.running = False
        logger.info("[Engine] Bot stopped cleanly.")

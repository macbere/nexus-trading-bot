"""Bot Engine - Core trading loop manager"""
import time
import signal
import logging
from dataclasses import dataclass, field

from bot.config_loader import load_config
from bot.exchange_factory import build_exchange
from bot.pair_engine import PairEngine

logger = logging.getLogger(__name__)


@dataclass
class BotState:
    running: bool = False
    tick_count: int = 0
    start_time: float = field(default_factory=time.time)
    last_error: str = ""


class BotEngine:
    def __init__(self):
        self.cfg = load_config()
        self.exchange = build_exchange(self.cfg)
        self.pair_engine = PairEngine(self.cfg, self.exchange)
        self.poll_secs = float(self.cfg.get("BOT_POLL_SECONDS", 60))
        self._stop = False
        self.bot_state = BotState()

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, *_):
        logger.warning("[Engine] Shutdown signal - stopping cleanly.")
        self._stop = True
        self.bot_state.running = False

    def _tick(self):
        try:
            self.bot_state.tick_count += 1
            logger.info(f"[Engine] Tick #{self.bot_state.tick_count}")
            self.pair_engine.scan_and_trade()
        except Exception as exc:
            self.bot_state.last_error = str(exc)
            logger.exception("[Engine] Unhandled exception: %s", exc)

    def run(self):
        logger.info("[Engine] NEXUS Bot starting | poll=%ss", self.poll_secs)
        self.bot_state.running = True
        self.bot_state.start_time = time.time()

        while not self._stop:
            try:
                self._tick()
            except Exception as e:
                logger.exception("[Engine] Tick error: %s", e)

            for _ in range(int(self.poll_secs)):
                if self._stop:
                    break
                time.sleep(1)

        self.bot_state.running = False
        logger.info("[Engine] Bot stopped cleanly.")

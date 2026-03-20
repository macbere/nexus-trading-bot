"""
main.py
────────────────────────────────────────────────────────────
Entry point.

Usage
─────
  # Run the trading bot only:
  python main.py

  # Run bot + API server together (dev / single-worker deploy):
  python main.py --with-api

PythonAnywhere scheduled task command:
  /home/macbere/.local/bin/python3.10 /home/macbere/trading_bot/main.py

PythonAnywhere web app (WSGI) — point to:
  /home/macbere/trading_bot/api/app.py  →  app object
"""

import argparse
import logging
import threading
import sys
import os

# ── Ensure logs directory exists ──────────────────────────
os.makedirs("logs", exist_ok=True)

# ── Logging setup ─────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run_bot() -> None:
    from bot.bot_engine import BotEngine
    engine = BotEngine()
    engine.run()


def run_api() -> None:
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host    = "0.0.0.0",
        port    = 8000,
        reload  = False,
        workers = 1,    # 1 worker = minimal CPU on free tier
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HFT Scalper Bot")
    parser.add_argument(
        "--with-api",
        action="store_true",
        help="Also start the FastAPI server in a background thread",
    )
    args = parser.parse_args()

    if args.with_api:
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        logger.info("[Main] FastAPI server started in background thread on :8000")

    run_bot()

"""NEXUS Trading Bot - Main Entry Point"""
import os
import time
import json
import logging
import threading

from flask import Flask, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/ping")
def ping():
    return jsonify({"status": "pong", "timestamp": time.time()})

@app.route("/")
def home():
    return "NEXUS Trading Bot is Running! 🚀"

@app.route("/status")
def status():
    return jsonify({"status": "healthy", "timestamp": time.time()})

def self_ping_loop():
    import urllib.request
    import ssl
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")
            if url and url != "http://localhost:8000":
                context = ssl._create_unverified_context()
                urllib.request.urlopen(f"{url}/ping", context=context, timeout=10)
                logger.info("🏓 Self-ping sent")
        except Exception as e:
            logger.debug(f"Ping error: {e}")
        time.sleep(840)

def run_bot():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        logger.info("✅ Config loaded")

        from bot.exchange_factory import build_exchange
        exchange = build_exchange(config)
        logger.info("✅ Exchange initialized")

        from bot.pair_engine import PairEngine
        from bot.position_monitor import PositionMonitor

        engine = PairEngine(config, exchange)
        logger.info("✅ PairEngine initialized")

        # Start position monitor background thread
        monitor = PositionMonitor(config)
        monitor.start()
        logger.info("✅ Position monitor started")

        poll_seconds = int(config.get("BOT_POLL_SECONDS", 60))
        logger.info(f"🚀 Bot running! Scanning every {poll_seconds}s")

        while True:
            try:
                engine.scan_and_trade()
                logger.info(f"⏳ Waiting {poll_seconds}s before next scan...")
                time.sleep(poll_seconds)
            except KeyboardInterrupt:
                logger.info("🔴 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Loop error: {e}")
                time.sleep(10)

    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("🚀 Starting NEXUS Trading Bot...")

    ping_thread = threading.Thread(target=self_ping_loop, daemon=True)
    ping_thread.start()

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🌐 Web server on port {port}")
    app.run(host="0.0.0.0", port=port)

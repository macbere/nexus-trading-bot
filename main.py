"""NEXUS Trading Bot - Main Entry Point - Single Engine"""
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

@app.route("/positions")
def positions():
    try:
        import json as j
        with open("config.json") as f:
            cfg = j.load(f)
        from bot.exchange_factory import build_exchange, get_positions, get_balance
        build_exchange(cfg)
        pos = get_positions(cfg)
        bal = get_balance(cfg)
        return jsonify({
            "balance": bal,
            "positions": pos,
            "count": len(pos)
        })
    except Exception as e:
        return jsonify({"error": str(e)})

def self_ping_loop():
    import urllib.request, ssl
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL", "")
            if url:
                ctx = ssl._create_unverified_context()
                urllib.request.urlopen(f"{url}/ping", context=ctx, timeout=10)
                logger.info("🏓 Self-ping sent")
        except Exception as e:
            logger.debug(f"Ping: {e}")
        time.sleep(840)

def run_bot():
    """Single bot loop - only one instance"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        logger.info("✅ Config loaded")

        from bot.exchange_factory import build_exchange
        build_exchange(config)
        logger.info("✅ Exchange initialized")

        # Single engine - new version only
        from bot.pair_engine import PairEngine
        engine = PairEngine(config)
        logger.info("✅ PairEngine initialized")

        # Position monitor
        from bot.position_monitor import PositionMonitor
        monitor = PositionMonitor(config)
        monitor.start()
        logger.info("✅ Position monitor started")

        poll = int(config.get("BOT_POLL_SECONDS", 60))
        logger.info(f"🚀 Bot running - scanning every {poll}s")

        while True:
            try:
                engine.scan_and_trade()
                logger.info(f"⏳ Waiting {poll}s before next scan...")
                time.sleep(poll)
            except KeyboardInterrupt:
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

    threading.Thread(target=self_ping_loop, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🌐 Web server on port {port}")
    app.run(host="0.0.0.0", port=port)

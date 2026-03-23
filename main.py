"""Minimal Trading Bot - Get it working first"""
import os
import time
import json
import logging
import threading
import pandas as pd
from flask import Flask, render_template, request, jsonify

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app for Render
app = Flask(__name__, static_folder="dashboard/static", static_url_path="/static", template_folder="templates")

@app.route('/ping')
def ping():
    return {"status": "pong", "timestamp": time.time()}

@app.route('/')
def home():
    return "Nexus Trading Bot is Running! 🚀"

@app.route('/status')
def status():
    return {"status": "healthy", "timestamp": time.time()}

def self_ping_loop():
    """Keep Render instance awake by pinging every 14 minutes"""
    import urllib.request
    import ssl
    while True:
        try:
            url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8000')
            if url and url != 'http://localhost:8000':
                context = ssl._create_unverified_context()
                urllib.request.urlopen(f"{url}/ping", context=context, timeout=10)
                logger.info("🔄 Self-ping sent")
        except Exception as e:
            logger.debug(f"Ping error (expected on first run): {e}")
        time.sleep(840)  # 14 minutes
def run_bot():
    """Main bot loop - loads config, connects to Bitget, scans & trades"""
    try:
        # Load config
        with open('config.json', 'r') as f:
            config = json.load(f)
        logger.info("✅ Config loaded")
        
        # Build exchange (Bitget futures)
        from bot.exchange_factory import build_exchange
        exchange = build_exchange(config)
        logger.info("✅ Exchange initialized")
        
        # Initialize PairEngine
        from bot.pair_engine import PairEngine
        engine = PairEngine(config, exchange)
        logger.info("✅ PairEngine initialized")
        
        # Main trading loop
        poll_seconds = config.get('BOT_POLL_SECONDS', 60)
        logger.info(f"🎉 Bot running! Scanning every {poll_seconds}s")
        
        while True:
            try:
                engine.scan_and_trade()
                time.sleep(poll_seconds)
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Loop error: {e}")
                time.sleep(10)
                
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("🚀 Starting Nexus Trading Bot...")
    
    # Start self-ping thread (keep Render awake)
    ping_thread = threading.Thread(target=self_ping_loop, daemon=True)
    ping_thread.start()
    
    # Start bot thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Run Flask server    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🌐 Web server listening on port {port}")
    app.run(host='0.0.0.0', port=port)

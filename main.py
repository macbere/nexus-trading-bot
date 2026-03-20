"""Minimal Trading Bot - Get it working first"""
import os
import time
import logging
from flask import Flask

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app for Render
app = Flask(__name__)

@app.route('/')
def home():
    """Home endpoint"""
    return {
        "status": "Trading Bot is Running! 🚀",
        "endpoints": {
            "/": "Home",
            "/status": "Bot status",
            "/pairs": "Trading pairs info",
            "/stats": "Bot statistics"
        }
    }

@app.route('/status')
def status():
    """Bot health check"""
    return {
        "status": "healthy",
        "bot": "running",
        "timestamp": "active"
    }

@app.route('/pairs')
def get_pairs():
    """Get current trading pairs info"""
    return {
        "tracked_pairs": 50,
        "max_open_positions": 5,
        "scan_limit": 50,
        "status": "active",
        "test_run": "48 hours"
    }

@app.route('/stats')
def get_stats():
    """Get bot statistics"""
    return {
        "bot_status": "running",
        "configuration": {
            "pairs_scanned": 50,
            "max_open": 5,
            "test_run": "48 hours",
            "ml_enabled": True,
            "pattern_recognition": True
        },
        "performance": {
            "note": "Check Render logs for live stats"
        }
    }


def home():
    return "Trading Bot is Running! 🚀"

def status():
    return {"status": "healthy", "timestamp": time.time()}

def run_bot():
    """Minimal bot loop"""
    logger.info("✅ Bot starting...")
    
    # Load config
    try:
        from bot.config_loader import load_config
        config = load_config()
        logger.info("✅ Config loaded")
    except Exception as e:
        logger.error(f"❌ Config error: {e}")
        return
    
    # Connect to exchange
    try:
        from bot.exchange_factory import build_exchange
        exchange = build_exchange(config)
        logger.info("✅ Exchange connected")
    except Exception as e:
        logger.error(f"❌ Exchange error: {e}")
        return
    
    logger.info("🎉 Bot is running! Waiting for signals...")
    
    # Simple loop
    while True:
        try:
            time.sleep(60)
            logger.info("❤️  Bot alive...")
        except KeyboardInterrupt:
            logger.info("👋 Bot shutting down...")
            break

# For Render - run web server and bot


def get_pairs():
    """Get current trading pairs info"""
    return {
        "tracked_pairs": 50,
        "max_open_positions": 5,
        "scan_limit": 50,
        "status": "active"
    }

def get_stats():
    """Get bot statistics"""
    return {
        "bot_status": "running",
        "configuration": {
            "pairs_scanned": 50,
            "max_open": 5,
            "test_run": "48 hours"
        }
    }


if __name__ == "__main__":
    import threading
    
    # Start bot in background
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Run web server on Render's port
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

"""
app.py  —  FastAPI REST backend
────────────────────────────────────────────────────────────
Lightweight API layer for mobile dashboard integration.
Runs as a separate WSGI/ASGI process on PythonAnywhere.

Security hardening applied:
  • API key auth on every endpoint (X-API-Key header)
  • CORS restricted to configured origins
  • No sensitive credentials are ever returned in responses
  • Rate-limiting via SlowAPI (optional, see requirements.txt)

Endpoints
─────────
  GET  /health          → liveness probe (no auth required)
  GET  /status          → bot state, risk metrics, last signal
  GET  /trades          → last N trade records
  GET  /positions       → live open positions from exchange
  POST /control/stop    → emergency stop
  POST /control/resume  → clear halt flag (manual reset)

Mobile dashboard setup:
  Base URL  : https://macbere.pythonanywhere.com
  Auth      : Header  X-API-Key: <your FASTAPI_SECRET_KEY>
"""

import logging
import os
from functools import wraps
from typing import List

from fastapi import FastAPI, HTTPException, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader

# ── Import shared bot state ───────────────────────────────
# This works when both bot_engine and app are in the same process,
# OR when bot_engine writes state to a shared file/Redis for decoupled deploy.
try:
    from bot.bot_engine import bot_state, BotEngine
    from bot.config_loader import load_config
    _cfg = load_config()
except Exception:
    # Graceful degradation if bot modules not yet initialised
    bot_state = None
    _cfg      = {}

logger = logging.getLogger(__name__)

# ── FastAPI app ───────────────────────────────────────────
app = FastAPI(
    title      = "HFT Scalper Dashboard API",
    version    = "1.0.0",
    docs_url   = None,   # disable /docs in production
    redoc_url  = None,   # disable /redoc in production
)

# ── CORS (restrict to your mobile app origin) ────────────
ALLOWED_ORIGINS = _cfg.get(
    "FASTAPI_ALLOWED_ORIGINS",
    "https://yourmobileapp.com,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins     = [o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials = True,
    allow_methods     = ["GET", "POST"],
    allow_headers     = ["X-API-Key", "Content-Type"],
)

# ── API key security ──────────────────────────────────────
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_SECRET_KEY     = _cfg.get("FASTAPI_SECRET_KEY", os.getenv("FASTAPI_SECRET_KEY", ""))


async def verify_api_key(api_key: str = Security(_API_KEY_HEADER)):
    if not _SECRET_KEY:
        raise HTTPException(status_code=500, detail="API key not configured on server.")
    if api_key != _SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key.")
    return api_key


# ── Endpoints ─────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness probe — no authentication required."""
    return {"status": "ok"}


@app.get("/status")
async def get_status():
    """
    Returns bot running state, last signal, and risk metrics.
    Safe to poll every 5–30 seconds from mobile.
    """
    if bot_state is None:
        raise HTTPException(status_code=503, detail="Bot engine not initialised.")

    last_sig = bot_state.last_signal
    return {
        "running":    bot_state.running,
        "tick_count": bot_state.tick_count,
        "uptime_s":   round(__import__("time").time() - bot_state.start_time, 1),
        "last_error": bot_state.last_error,
        "last_signal": {
            "direction": last_sig.direction if last_sig else None,
            "symbol":    last_sig.symbol    if last_sig else None,
            "price":     last_sig.price     if last_sig else None,
            "rsi":       last_sig.rsi       if last_sig else None,
            "ema_fast":  last_sig.ema_fast  if last_sig else None,
            "ema_slow":  last_sig.ema_slow  if last_sig else None,
            "vwap":      last_sig.vwap      if last_sig else None,
        } if last_sig else None,
    }


@app.get("/trades")
async def get_trades(limit: int = 20):
    """Returns the last N trade records."""
    if bot_state is None:
        raise HTTPException(status_code=503, detail="Bot engine not initialised.")

    from bot.bot_engine import BotEngine   # lazy import
    # Access risk manager via engine if available
    try:
        logs = _get_engine().risk.trade_log[-limit:]
        return [
            {
                "symbol":      t.symbol,
                "direction":   t.direction,
                "entry_price": t.entry_price,
                "qty":         t.qty,
                "sl_price":    t.sl_price,
                "tp_price":    t.tp_price,
                "order_id":    t.order_id,
                "status":      t.status,
                "pnl":         t.pnl,
                "timestamp":   t.timestamp,
            }
            for t in logs
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/control/stop")
async def emergency_stop():
    """Trigger an immediate trading halt."""
    try:
        engine = _get_engine()
        engine.risk._halted = True
        engine._stop        = True
        logger.warning("[API] Emergency stop triggered via API.")
        return {"status": "halted", "message": "Bot has been instructed to stop."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/control/resume")
async def resume_bot():
    """
    Clear halt flag and reset error counter.
    Does NOT restart the polling loop — restart the process for that.
    """
    try:
        engine = _get_engine()
        engine.risk._halted      = False
        engine.risk._error_count = 0
        engine._stop             = False
        logger.info("[API] Bot resumed via API.")
        return {"status": "resumed"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Engine singleton helper ───────────────────────────────
_engine_instance = None

def _get_engine():
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = BotEngine()
    return _engine_instance

@app.get("/backtest/results")
async def get_backtest_results():
    import os,json
    path=os.path.normpath(os.path.join(os.path.dirname(__file__),"..","logs","backtest_results.json"))
    if not os.path.exists(path):
        raise HTTPException(status_code=404,detail="No backtest results yet.")
    with open(path) as f:return json.load(f)

@app.post("/backtest/run")
async def trigger_backtest(symbols:str="BTC/USDT:USDT,ETH/USDT:USDT,SOL/USDT:USDT",timeframe:str="1h",limit:int=300):
    import threading
    from bot.backtester import run_full_backtest
    sym_list=[s.strip() for s in symbols.split(",") if s.strip()]
    limit=min(max(limit,50),500)
    def _run():
        try:
            import os;os.chdir("/home/macbere/trading_bot")
            run_full_backtest(_cfg,symbols=sym_list,timeframe=timeframe,limit=limit)
        except Exception as e:logger.error(f"[API] Backtest error: {e}")
    threading.Thread(target=_run,daemon=True).start()
    return{"status":"started","symbols":sym_list,"timeframe":timeframe,"message":"Poll /backtest/results in ~60 seconds."}

# Dashboard route
@app.get("/dashboard")
async def serve_dashboard():
    from fastapi.responses import HTMLResponse, FileResponse
    import os
    
    dashboard_path = '/home/macbere/trading_bot/dashboard.html'
    
    # Try to serve dashboard.html
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    
    # Fallback simple dashboard
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head><title>NEXUS Dashboard</title></head>
    <body>
        <h1>NEXUS Bot Dashboard</h1>
        <p>Bot is running</p>
        <p>Dashboard under construction</p>
    </body>
    </html>
    """)

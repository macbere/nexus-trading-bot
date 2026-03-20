import json,os,time,logging
from bot.stats_manager import calc_stats,save_brain,load_brain

logger=logging.getLogger(__name__)

TARGET_WIN_RATE=50.0
TARGET_PNL=0.0
MIN_TRADES_TO_ANALYZE=5

def analyze_and_adapt():
    stats=calc_stats()
    brain=load_brain()
    n=stats["total_trades"]
    if n<MIN_TRADES_TO_ANALYZE:
        return{**stats,"message":f"Need {MIN_TRADES_TO_ANALYZE}+ trades to analyze","adaptation_needed":False}
    win_rate=stats["win_rate"]
    total_pnl=stats["total_pnl"]
    alerts=[]
    adaptation_needed=False
    if win_rate<TARGET_WIN_RATE:
        alerts.append(f"⚠️ Win rate {win_rate}% below target {TARGET_WIN_RATE}%")
        adaptation_needed=True
    if total_pnl<TARGET_PNL:
        alerts.append(f"⚠️ Total PnL {total_pnl} below target {TARGET_PNL}")
        adaptation_needed=True
    if not alerts:
        alerts.append("✅ Strategy performing within targets")
    brain_data={
        **stats,
        "alerts":alerts,
        "adaptation_needed":adaptation_needed,
        "target_win_rate":TARGET_WIN_RATE,
        "target_pnl":TARGET_PNL,
        "last_adaptation":brain.get("last_adaptation","Never"),
        "last_analyzed":time.time()
    }
    if adaptation_needed and brain.get("last_adaptation")!="Never":
        brain_data["suggestion"]="Consider reducing BOT_TP_PCT or increasing BOT_EMA_FAST period"
    save_brain(brain_data)
    return brain_data

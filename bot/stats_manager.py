import json,os,time
from datetime import datetime

JOURNAL=os.path.expanduser("~/trading_bot/logs/trade_journal.json")
BRAIN=os.path.expanduser("~/trading_bot/logs/nexus_brain.json")

def load_trades():
    try:
        if os.path.exists(JOURNAL):
            with open(JOURNAL) as f:return json.load(f)
    except:pass
    return[]

def calc_stats():
    trades=load_trades()
    if not trades:
        return{"total_trades":0,"win_rate":0,"avg_win":0,"avg_loss":0,
               "total_pnl":0,"winners":0,"losers":0,"last_updated":time.time()}
    closed=[t for t in trades if t.get("pnl") is not None]
    if not closed:
        return{"total_trades":0,"win_rate":0,"avg_win":0,"avg_loss":0,
               "total_pnl":0,"winners":0,"losers":0,"last_updated":time.time()}
    winners=[t for t in closed if float(t.get("pnl",0))>0]
    losers=[t for t in closed if float(t.get("pnl",0))<=0]
    n=len(closed)
    win_rate=round(len(winners)/n*100,1) if n else 0
    avg_win=round(sum(float(t["pnl"]) for t in winners)/len(winners),4) if winners else 0
    avg_loss=round(sum(float(t["pnl"]) for t in losers)/len(losers),4) if losers else 0
    total_pnl=round(sum(float(t.get("pnl",0)) for t in closed),4)
    return{
        "total_trades":n,"win_rate":win_rate,"avg_win":avg_win,
        "avg_loss":avg_loss,"total_pnl":total_pnl,
        "winners":len(winners),"losers":len(losers),
        "last_updated":time.time()
    }

def get_recent_trades(limit=50,period_hours=None):
    trades=load_trades()
    if period_hours:
        cutoff=time.time()-period_hours*3600
        trades=[t for t in trades if float(t.get("timestamp",0))>cutoff]
    return trades[-limit:]

def save_brain(data):
    try:
        os.makedirs(os.path.dirname(BRAIN),exist_ok=True)
        with open(BRAIN,"w") as f:json.dump(data,f,indent=2)
    except:pass

def load_brain():
    try:
        if os.path.exists(BRAIN):
            with open(BRAIN) as f:return json.load(f)
    except:pass
    return{}

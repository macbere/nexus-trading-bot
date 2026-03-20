import json,time,logging,os
from dataclasses import dataclass
from typing import List,Optional
logger=logging.getLogger(__name__)

def ema(prices,period):
    result,k=[],2/(period+1)
    for i,p in enumerate(prices):
        if i<period-1:result.append(None)
        elif i==period-1:result.append(sum(prices[:period])/period)
        else:result.append(p*k+result[-1]*(1-k))
    return result

def rsi(prices,period=14):
    result=[None]*period
    for i in range(period,len(prices)):
        w=prices[i-period:i+1]
        g=[max(w[j]-w[j-1],0) for j in range(1,len(w))]
        l=[max(w[j-1]-w[j],0) for j in range(1,len(w))]
        ag,al=sum(g)/period,sum(l)/period
        result.append(100.0 if al==0 else round(100-100/(1+ag/al),2))
    return result

def bollinger(prices,period=20,mult=2.0):
    up,lo,mid=[],[],[]
    for i in range(len(prices)):
        if i<period-1:up.append(None);lo.append(None);mid.append(None)
        else:
            w=prices[i-period+1:i+1];m=sum(w)/period
            sd=(sum((x-m)**2 for x in w)/period)**0.5
            mid.append(m);up.append(m+mult*sd);lo.append(m-mult*sd)
    return up,mid,lo

def sig_ema(closes,i,cfg):
    fast=int(cfg.get("BOT_EMA_FAST",9));slow=int(cfg.get("BOT_EMA_SLOW",21))
    rob=float(cfg.get("BOT_RSI_OB",60));ros=float(cfg.get("BOT_RSI_OS",40))
    if i<slow:return("FLAT",closes[i])
    ef=ema(closes[:i+1],fast)[-1];es=ema(closes[:i+1],slow)[-1]
    r=(rsi(closes[:i+1],14) or [50])[-1] or 50
    if ef>es and r<rob:return("LONG",closes[i])
    elif ef<es and r>ros:return("SHORT",closes[i])
    return("FLAT",closes[i])

def sig_bb(closes,i,cfg):
    period=int(cfg.get("BOT_BB_PERIOD",20))
    if i<period:return("FLAT",closes[i])
    up,_,lo=bollinger(closes[:i+1],period)
    u,l=up[-1],lo[-1]
    if u is None:return("FLAT",closes[i])
    if closes[i]<l:return("LONG",closes[i])
    elif closes[i]>u:return("SHORT",closes[i])
    return("FLAT",closes[i])

def sig_multi(closes,i,cfg):
    se=sig_ema(closes,i,cfg);sb=sig_bb(closes,i,cfg)
    if se[0]==sb[0] and se[0]!="FLAT":return se
    return("FLAT",closes[i])

def run_backtest(symbol,candles,strategy,cfg):
    tp=float(cfg.get("BOT_TARGET_ROE",20))
    sl=float(cfg.get("BOT_SL_ROE",20))
    closes=[c["close"] for c in candles]
    fns={"EMA":sig_ema,"BB":sig_bb,"MULTI":sig_multi}
    fn=fns[strategy]
    trades=[];pos=None;equity=[1.0]
    for i in range(1,len(closes)):
        p=closes[i]
        if pos:
            pnl=(p-pos["entry"])/pos["entry"]*100 if pos["dir"]=="LONG" else (pos["entry"]-p)/pos["entry"]*100
            if pnl>=tp or pnl<=-sl:
                pos["exit"]=p;pos["pnl"]=round(pnl,4);pos["reason"]="TP" if pnl>=tp else "SL"
                trades.append(pos);equity.append(equity[-1]*(1+pnl/100));pos=None
            continue
        d,pr=fn(closes,i,cfg)
        if d in("LONG","SHORT"):pos={"dir":d,"entry":p,"idx":i}
    if pos:
        pnl=(closes[-1]-pos["entry"])/pos["entry"]*100 if pos["dir"]=="LONG" else (pos["entry"]-closes[-1])/pos["entry"]*100
        pos["exit"]=closes[-1];pos["pnl"]=round(pnl,4);pos["reason"]="OPEN"
        trades.append(pos);equity.append(equity[-1]*(1+pnl/100))
    n=len(trades)
    wins=[t for t in trades if t["pnl"]>0]
    best=max(trades,key=lambda t:t["pnl"],default=None)
    worst=min(trades,key=lambda t:t["pnl"],default=None)
    step=max(1,len(equity)//100)
    return{
        "symbol":symbol,"strategy":strategy,"candles_used":len(candles),
        "total_trades":n,"win_rate_pct":round(len(wins)/n*100,1) if n else 0,
        "total_pnl_pct":round(sum(t["pnl"] for t in trades),2),
        "best_trade":{"pnl_pct":best["pnl"],"direction":best["dir"],"reason":best["reason"]} if best else None,
        "worst_trade":{"pnl_pct":worst["pnl"],"direction":worst["dir"],"reason":worst["reason"]} if worst else None,
        "equity_curve":[round(v,4) for v in equity[::step]],
        "trades":[{"direction":t["dir"],"entry":t["entry"],"exit":t["exit"],"pnl_pct":t["pnl"],"reason":t["reason"]} for t in trades]
    }

def fetch_candles(exchange,symbol,timeframe="1h",limit=300):
    try:
        raw=__import__("bot.exchange_factory", fromlist=["fetch_ohlcv_direct"]).fetch_ohlcv_direct(symbol, timeframe, limit=limit)
        return[{"timestamp":r[0],"open":r[1],"high":r[2],"low":r[3],"close":r[4]} for r in raw if r[4]]
    except Exception as e:
        logger.error(f"[Backtest] fetch error {symbol}: {e}");return[]

def run_full_backtest(cfg,symbols=None,timeframe="1h",limit=300):
    from bot.exchange_factory import build_exchange
    exchange=build_exchange(cfg)
    if not symbols:symbols=[cfg.get("BOT_SYMBOL","BTC/USDT:USDT")]
    results={}
    for sym in symbols:
        logger.info(f"[Backtest] {sym} fetching {limit} candles...")
        candles=fetch_candles(exchange,sym,timeframe,limit)
        if len(candles)<50:logger.warning(f"[Backtest] Not enough candles for {sym}");continue
        results[sym]={}
        for strat in["EMA","BB","MULTI"]:
            r=run_backtest(sym,candles,strat,cfg)
            results[sym][strat]=r
            logger.info(f"[Backtest] {sym}/{strat} trades={r['total_trades']} win={r['win_rate_pct']}% pnl={r['total_pnl_pct']}%")
    output={"timestamp":time.time(),"timeframe":timeframe,"candles_used":limit,"results":results}
    os.makedirs("logs",exist_ok=True)
    with open("logs/backtest_results.json","w") as f:json.dump(output,f,indent=2)
    logger.info("[Backtest] Saved to logs/backtest_results.json")
    return output

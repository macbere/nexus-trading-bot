import sys, json, time, os, re
sys.path.insert(0, '/home/macbere/trading_bot')

from flask import Flask, request, jsonify, send_file
from bot.config_loader import load_config

app = Flask(__name__)
cfg = load_config()
API_KEY  = cfg.get("FASTAPI_SECRET_KEY", "")
LOG_FILE = "/home/macbere/trading_bot/logs/bot.log"
CFG_FILE = "/home/macbere/trading_bot/config.json"
APP_FILE = "/home/macbere/trading_bot/nexus_v2.html"

def check_key():
    return request.headers.get("X-API-Key") == API_KEY

def parse_log():
    result = {"running": False, "last_signal": None, "last_error": "", "tick_count": 0}
    if not os.path.exists(LOG_FILE):
        return result
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()[-100:]
    try:
        from datetime import datetime
        log_time = datetime.strptime(lines[-1][:23], "%Y-%m-%d %H:%M:%S,%f")
        result["running"] = time.time() - log_time.timestamp() < 600
    except:
        pass
    for line in reversed(lines):
        if "Signal" in line and (">" in line):
            try:
                m_dir   = re.search(r"Signal\s*[\-=>→]+\s*(\w+)", line)
                m_price = re.search(r"price=([\d.]+)", line)
                m_rsi   = re.search(r"RSI=([\d.]+)", line)
                m_emaf  = re.search(r"EMA_F=([\d.]+)", line)
                m_emas  = re.search(r"EMA_S=([\d.]+)", line)
                if m_dir and m_price:
                    result["last_signal"] = {
                        "direction": m_dir.group(1),
                        "price":     float(m_price.group(1)),
                        "rsi":       float(m_rsi.group(1))  if m_rsi  else None,
                        "ema_fast":  float(m_emaf.group(1)) if m_emaf else None,
                        "ema_slow":  float(m_emas.group(1)) if m_emas else None,
                        "timestamp": line[:23]
                    }
            except:
                pass
            break
    result["tick_count"] = sum(1 for l in lines if "Signal" in l)
    for line in reversed(lines):
        if "[ERROR]" in line or "[CRITICAL]" in line:
            result["last_error"] = line.strip()[-120:]
            break
    return result


@app.route("/balance")
def balance():
    if not check_key():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        from bot.exchange_factory import get_balance
        bal = get_balance(cfg)
        return jsonify({
            "total":      round(bal.get("total", 0), 4),
            "free":       round(bal.get("free",  0), 4),
            "used":       round(bal.get("used",  0), 4),
            "unrealized": round(bal.get("unrealized", 0), 4),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/status")
def status():
    if not check_key():
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify(parse_log())

@app.route("/trades")
def trades():
    if not check_key():
        return jsonify({"error": "Unauthorized"}), 403
    trades_list = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        for line in reversed(lines):
            if ("Signal" in line or "signal" in line) and "FLAT" not in line:
                try:
                    m_dir   = re.search(r"Signal\s*[\-=>→]+\s*(\w+)", line)
                    m_price = re.search(r"price=([\d.]+)", line)
                    m_rsi   = re.search(r"RSI=([\d.]+)", line)
                    if m_dir and m_price and m_dir.group(1) != "FLAT":
                        trades_list.append({
                            "timestamp": line[:23],
                            "direction": m_dir.group(1),
                            "price":     float(m_price.group(1)),
                            "rsi":       float(m_rsi.group(1)) if m_rsi else None,
                        })
                except:
                    pass
            if len(trades_list) >= 20:
                break
    return jsonify(trades_list)

@app.route("/positions")
def positions():
    if not check_key():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        from bot.exchange_factory import build_exchange
        ex     = build_exchange(cfg)
        from bot.exchange_factory import get_positions, get_balance
        raw_pos = get_positions(cfg)
        raw = [{"symbol":p["symbol"],"side":p["side"],"contracts":p["size"],"entryPrice":p["entry"],"markPrice":p["mark"],"unrealizedPnl":p["pnl"],"percentage":p["roe"],"initialMargin":0,"liquidationPrice":None} for p in raw_pos]
        result = []
        for p in raw:
            size = float(p.get("contracts", 0) or 0)
            if size > 0:
                result.append({
                    "symbol":      p.get("symbol"),
                    "side":        p.get("side"),
                    "size":        size,
                    "entry_price": p.get("entryPrice"),
                    "mark_price":  p.get("markPrice"),
                    "pnl":         round(float(p.get("unrealizedPnl", 0) or 0), 4),
                    "pnl_pct":     round(float(p.get("percentage",    0) or 0), 2),
                    "margin":      round(float(p.get("initialMargin",  0) or 0), 4),
                    "liq_price":   p.get("liquidationPrice"),
                })
        bal_data = get_balance(cfg)
        usdt = round(bal_data.get("free", 0), 4)
        return jsonify({"positions": result, "balance": round(usdt, 4)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/control/stop", methods=["POST"])
def stop():
    if not check_key():
        return jsonify({"error": "Unauthorized"}), 403
    os.system("pkill -f main.py; pkill -f watchdog")
    return jsonify({"status": "Bot stopped"})

@app.route("/manifest.json")
def manifest():
    return jsonify({"name":"NEXUS HFT Bot","short_name":"NEXUS",
                    "start_url":"/dashboard","display":"standalone",
                    "background_color":"#0a0a0f","theme_color":"#0a0a0f"})

@app.route("/dashboard")
@app.route("/app")
def mobile_app():
    if os.path.exists(APP_FILE):
        return send_file(APP_FILE, mimetype="text/html")
    return "<h2>App file not found</h2>", 404


@app.route('/scanner')
def scanner():
    if not check_key():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        import json, os
        log_file = "/home/macbere/trading_bot/logs/bot.log"
        top_pairs, scores = [], []
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                lines = f.readlines()
            for line in reversed(lines):
                if "Top pairs this hour" in line:
                    import re
                    m = re.search(r"Top pairs.*: (\[.*\])", line)
                    if m:
                        import ast
                        top_pairs = ast.literal_eval(m.group(1))
                    break
            for line in reversed(lines[-200:]):
                if "[Scanner] #" in line:
                    scores.append(line.strip()[-100:])
                if len(scores) >= 3:
                    break
        return jsonify({
            "top_pairs": top_pairs,
            "scores":    scores,
            "max_trades": 3
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/admin/roe', methods=['POST'])
def set_roe():
    if not check_key():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        data       = request.get_json()
        target_roe = str(data.get('target_roe', 25))
        sl_roe     = str(data.get('sl_roe',     10))
        with open(CFG_FILE, 'r') as f:
            cfg_data = json.load(f)
        cfg_data['BOT_TARGET_ROE'] = target_roe
        cfg_data['BOT_SL_ROE']     = sl_roe
        with open(CFG_FILE, 'w') as f:
            json.dump(cfg_data, f, indent=2)
        # No restart needed — monitor reloads config every tick!
        return jsonify({
            "status":     "ok",
            "target_roe": target_roe,
            "sl_roe":     sl_roe
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/config')
def get_config():
    if not check_key():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        with open(CFG_FILE, 'r') as f:
            cfg_data = json.load(f)
        safe_keys = [
            'BOT_SYMBOL','BOT_TIMEFRAME','BOT_EMA_FAST','BOT_EMA_SLOW',
            'BOT_RSI_PERIOD','BOT_RSI_OB','BOT_RSI_OS','BOT_RISK_PCT',
            'BOT_SL_PCT','BOT_TP_PCT','BOT_MAX_POS_USD','BOT_POLL_SECONDS',
            'BOT_TARGET_ROE','BOT_SL_ROE','BOT_BB_PERIOD','BOT_BB_STD',
            'BOT_SANDBOX','BOT_MAX_ERRORS','BOT_MAX_DAILY_LOSS_USD'
        ]
        return jsonify({k: cfg_data.get(k,'') for k in safe_keys})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

application = app

@app.route('/analytics')
def analytics():
    if not check_key():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        import sys
        sys.path.insert(0, '/home/macbere/trading_bot')
        from bot.adaptive_strategy import analyze_and_adapt
        result = analyze_and_adapt()
        journal_file = "/home/macbere/trading_bot/logs/trade_journal.json"
        if os.path.exists(journal_file):
            with open(journal_file, "r") as f:
                trades = json.load(f)
            total_pnl = sum(t['pnl'] for t in trades)
            result['total_pnl']   = round(total_pnl, 4)
            result['total_trades'] = len(trades)
        return jsonify(result or {"message": "Need 10+ trades to analyze"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/trade/manual',methods=['POST'])
def manual_trade():
    if not check_key():return jsonify({"error":"Unauthorized"}),403
    try:
        import sys,math
        sys.path.insert(0,'/home/macbere/trading_bot')
        from bot.exchange_factory import build_exchange
        from bot.config_loader import load_config
        data=request.get_json()
        symbol=data.get('symbol','BTC/USDT:USDT')
        side=data.get('side','buy')
        qty_usd=float(data.get('qty_usd',6))
        order_type=data.get('order_type','market')
        price=data.get('price',None)
        cfg=load_config()
        ex=build_exchange(cfg)
        from bot.exchange_factory import fetch_ohlcv_direct
        _c = fetch_ohlcv_direct(symbol, '1m', limit=1)
        mark = float(_c[-1][4]) if _c else 1.0
        qty=math.ceil((qty_usd/mark)*10)/10
        params={"tdMode":"cross"}
        if order_type=='market':
            order=ex.create_order(symbol,'market',side,qty,None,params)
        else:
            order=ex.create_order(symbol,'limit',side,qty,float(price),params)
        return jsonify({"status":"ok","order_id":order.get('id','--'),"qty":qty})
    except Exception as e:return jsonify({"error":str(e)}),500

@app.route('/trade/close',methods=['POST'])
def close_trade():
    if not check_key():return jsonify({"error":"Unauthorized"}),403
    try:
        import sys
        sys.path.insert(0,'/home/macbere/trading_bot')
        from bot.exchange_factory import build_exchange
        from bot.config_loader import load_config
        data=request.get_json()
        symbol=data.get('symbol')
        side=data.get('side','long')
        contracts=float(data.get('contracts',0))
        cfg=load_config()
        ex=build_exchange(cfg)
        close_side='sell' if side.lower()=='long' else 'buy'
        order=ex.create_order(symbol,'market',close_side,contracts,None,{"reduceOnly":True})
        return jsonify({"status":"ok","order_id":order.get('id','--')})
    except Exception as e:return jsonify({"error":str(e)}),500

@app.route('/admin/config/update',methods=['POST'])
def update_config():
    if not check_key():return jsonify({"error":"Unauthorized"}),403
    try:
        import json
        data=request.get_json()
        allowed=['BOT_MAX_POS_USD','BOT_POLL_SECONDS','BOT_RISK_PCT','BOT_MAX_DAILY_LOSS_USD']
        with open(CFG_FILE,'r') as f:cfg=json.load(f)
        for k,v in data.items():
            if k in allowed:cfg[k]=str(v)
        with open(CFG_FILE,'w') as f:json.dump(cfg,f,indent=2)
        return jsonify({"status":"ok"})
    except Exception as e:return jsonify({"error":str(e)}),500

@app.route('/control/resume',methods=['POST'])
def resume_bot():
    if not check_key():return jsonify({"error":"Unauthorized"}),403
    try:
        import subprocess
        subprocess.Popen('pkill -f main.py; pkill -f watchdog; sleep 2; cd /home/macbere/trading_bot && nohup bash watchdog.sh >> logs/watchdog.log 2>&1 &', shell=True)
        return jsonify({"status":"started"})
    except Exception as e:return jsonify({"error":str(e)}),500

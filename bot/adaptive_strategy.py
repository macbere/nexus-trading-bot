import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
JOURNAL = BASE_DIR / "logs" / "trade_journal.json"
CONFIG = BASE_DIR / "config.json"

def analyze_and_adapt():
    """Read trade journal and auto-tune RSI/TP/SL settings."""
    if not JOURNAL.exists():
        return

    try:
        with JOURNAL.open("r", encoding="utf-8") as f:
            trades = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("[Adapt] Could not read trade journal: %s", exc)
        return

    if len(trades) < 10:
        logger.info("[Adapt] Need at least 10 trades to adapt — currently have %d", len(trades))
        return

    # Last 20 trades analysis
    recent = trades[-20:]
    wins   = [t for t in recent if t['pnl'] > 0]
    losses = [t for t in recent if t['pnl'] <= 0]
    win_rate = len(wins) / len(recent) * 100
    avg_win  = sum(t['pnl'] for t in wins)   / len(wins)   if wins   else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0

    logger.info(f"[Adapt] Win rate: {win_rate:.1f}% | Avg win: ${avg_win:.4f} | Avg loss: ${avg_loss:.4f}")

    try:
        with CONFIG.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("[Adapt] Could not read config: %s", exc)
        return

    changed = False

    # If win rate below 40% — tighten RSI bands (be more selective)
    if win_rate < 40:
        new_ob = min(float(cfg.get('BOT_RSI_OB', 60)) + 2, 70)
        new_os = max(float(cfg.get('BOT_RSI_OS', 40)) - 2, 30)
        cfg['BOT_RSI_OB'] = str(new_ob)
        cfg['BOT_RSI_OS'] = str(new_os)
        logger.info(f"[Adapt] Win rate low — tightening RSI to {new_os}/{new_ob}")
        changed = True

    # If win rate above 65% — loosen RSI bands (trade more often)
    elif win_rate > 65:
        new_ob = max(float(cfg.get('BOT_RSI_OB', 60)) - 1, 55)
        new_os = min(float(cfg.get('BOT_RSI_OS', 40)) + 1, 45)
        cfg['BOT_RSI_OB'] = str(new_ob)
        cfg['BOT_RSI_OS'] = str(new_os)
        logger.info(f"[Adapt] Win rate high — loosening RSI to {new_os}/{new_ob}")
        changed = True

    # If average loss > average win — widen TP
    if wins and losses and abs(avg_loss) > avg_win:
        new_tp = min(float(cfg.get('BOT_TP_PCT', 2.0)) + 0.2, 4.0)
        cfg['BOT_TP_PCT'] = str(round(new_tp, 1))
        logger.info(f"[Adapt] Losses exceeding wins — widening TP to {new_tp}%")
        changed = True

    if changed:
        with CONFIG.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        logger.info("[Adapt] Config updated with new parameters")

    return {
        "win_rate":  round(win_rate, 1),
        "avg_win":   round(avg_win, 4),
        "avg_loss":  round(avg_loss, 4),
        "total":     len(recent),
        "adapted":   changed
    }

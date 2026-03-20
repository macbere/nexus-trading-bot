"""
config_loader.py
────────────────────────────────────────────────────────────
Secure configuration loader.

Priority chain (highest → lowest):
  1. Environment variables  (recommended for PythonAnywhere)
  2. config.json            (local development only)

NEVER commit config.json to source control.
Add it to .gitignore immediately.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── Path resolution ───────────────────────────────────────
_BASE_DIR   = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _BASE_DIR / "config.json"


def _load_from_env() -> Dict[str, Any]:
    """Pull every BOT_* and BITGET_* variable from the process environment."""
    return {k: v for k, v in os.environ.items()
            if k.startswith(("BITGET_", "BOT_", "FASTAPI_"))}


def _load_from_file(path: Path = _CONFIG_FILE) -> Dict[str, Any]:
    """
    Load config.json.  File must be chmod 600 on PythonAnywhere:
        chmod 600 /home/macbere/trading_bot/config.json
    """
    if not path.exists():
        logger.debug("config.json not found – skipping file loader.")
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("Loaded configuration from %s", path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to parse config.json: %s", exc)
        return {}


def load_config() -> Dict[str, Any]:
    """
    Merge file config + env overrides.
    Environment variables always win (12-factor compliance).
    """
    cfg: Dict[str, Any] = _load_from_file()
    env_cfg = _load_from_env()

    # Env vars override file values
    cfg.update(env_cfg)

    _validate(cfg)
    return cfg


def _validate(cfg: Dict[str, Any]) -> None:
    """Raise early if critical keys are missing or still placeholder."""
    required = ["BITGET_API_KEY", "BITGET_SECRET", "BITGET_PASSWORD"]
    placeholders = {"YOUR_API_KEY_HERE", "YOUR_SECRET_HERE", "YOUR_PASSWORD_HERE", ""}

    for key in required:
        val = cfg.get(key, "")
        if val in placeholders:
            raise EnvironmentError(
                f"[Config] '{key}' is missing or still a placeholder. "
                "Set it in config.json or as an environment variable before starting the bot."
            )
    logger.info("[Config] All required credentials validated ✓")

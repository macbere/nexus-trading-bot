# Nexus Trading Bot

Nexus Trading Bot is a Bitget futures trading bot with a lightweight Flask status server, a market scanner, and a pair-trading execution loop.

## What is included

- Flask web app with `/`, `/ping`, `/status`, and `/positions`
- Bitget REST helpers for balances, positions, candles, and order placement
- Market scanner and pair trader pipeline
- Position monitor for basic exit management

## Requirements

- Python 3.12+
- A Bitget Demo API key with futures trading permission for the first phase

## Setup

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `config.template.json` to `config.json`.
4. Fill in your Bitget credentials and bot settings.

If you prefer not to edit JSON manually on Windows, run
`powershell -ExecutionPolicy Bypass -File scripts/configure_demo.ps1`. It
prompts securely and updates the local ignored configuration file.

For safe initial testing, create a Demo API key in Bitget Demo Trading mode and
keep `BITGET_DEMO=true` and `BOT_ALLOW_LIVE_TRADING=false`. Bitget requires the
`paptrading: 1` header for Demo REST requests, which the application adds
automatically. Live trading remains blocked unless both demo mode is disabled
and `BOT_ALLOW_LIVE_TRADING=true` is explicitly set.

## Run locally

```bash
python main.py
```

The app listens on `PORT` if it is provided, otherwise it defaults to `8000`.

## Configuration

The bot reads configuration from `config.json` and environment variables.

Environment variables override the file values, so you can keep secrets out of the repo.

## Notes

- `config.json` is ignored by git.
- Runtime logs are written under `logs/`.
- Never grant withdrawal permission to the API key; use IP allowlisting where available.
- Several legacy modules remain in the tree for backwards compatibility, but the main execution path is `main.py`.

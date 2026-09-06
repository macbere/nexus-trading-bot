import json
import os
from pathlib import Path


path = Path(os.environ["NEXUS_CONFIG_PATH"])
config = json.loads(path.read_text(encoding="utf-8"))
config.update(
    {
        "BITGET_API_KEY": os.environ["NEXUS_DEMO_API_KEY"],
        "BITGET_SECRET": os.environ["NEXUS_DEMO_SECRET"],
        "BITGET_PASSWORD": os.environ["NEXUS_DEMO_PASSWORD"],
        "BITGET_DEMO": "true",
        "BOT_ALLOW_LIVE_TRADING": "false",
        "BOT_SANDBOX": "true",
    }
)
path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
print("Demo configuration updated successfully. Credentials were not printed.")

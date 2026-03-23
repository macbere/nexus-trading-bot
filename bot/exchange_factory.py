"""Exchange Factory - Initialize trading exchange"""
import ccxt
import json

def build_exchange(config=None):
    """Build and return exchange instance"""
    if config is None:
        with open('config.json', 'r') as f:
            config = json.load(f)
    
    # Initialize Bitget exchange for futures trading
    exchange = ccxt.bitget({
        'apiKey': config.get('API_KEY', config.get('BITGET_API_KEY', '')),
        'secret': config.get('API_SECRET', config.get('BITGET_SECRET', '')),
        'password': config.get('BITGET_PASSWORD', ''),
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',  # Use futures/swap markets
            'adjustForTimeDifference': True,
        }
    })
    
    # Disable proxy if configured (can cause connection issues)
    exchange.proxy = None
    exchange.httpsProxy = None
    exchange.httpProxy = None
    
    print(f"✅ Bitget exchange initialized for futures trading")
    return exchange

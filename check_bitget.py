"""Check Bitget connection and API response format"""
import ccxt
import json

try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    print("=== BITGET CONNECTION TEST ===")
    
    # Initialize Bitget exchange
    exchange = ccxt.bitget({
        'apiKey': config.get('API_KEY', ''),
        'secret': config.get('API_SECRET', ''),
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',  # Use futures/swap
        }
    })
    
    # Test connection
    print("1. Testing connection...")
    balance = exchange.fetch_balance()
    print(f"   ✅ Connected! USDT Balance: {balance.get('USDT', {}).get('free', 0)}")
    
    # Test ticker fetch
    print("\n2. Testing ticker fetch for GALA/USDT:USDT...")
    ticker = exchange.fetch_ticker('GALA/USDT:USDT')
    print(f"   ✅ Ticker received!")
    print(f"   Keys: {list(ticker.keys())[:10]}")
    print(f"   Last: {ticker.get('last')}")
    print(f"   Close: {ticker.get('close')}")
    print(f"   Bid: {ticker.get('bid')}")
    print(f"   Ask: {ticker.get('ask')}")    
    # Test market loading
    print("\n3. Loading markets...")
    markets = exchange.load_markets()
    usdt_futures = [k for k in markets.keys() if ':USDT' in k]
    print(f"   ✅ Found {len(usdt_futures)} USDT futures pairs")
    print(f"   Sample pairs: {usdt_futures[:5]}")
    
    print("\n✅ ALL TESTS PASSED - Bitget is working correctly!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

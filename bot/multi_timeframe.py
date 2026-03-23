"""Multi-Timeframe Analysis Module"""
import pandas as pd
import time

class MultiTimeframeAnalyzer:
    def __init__(self, exchange, config):
        self.exchange = exchange
        self.config = config
        self.timeframes = ["15m", "1h", "4h", "1d"]

    def analyze_all_timeframes(self, symbol):
        try:
            results = {}
            for tf in self.timeframes:
                result = self.analyze_timeframe(symbol, tf)
                if result:
                    results[tf] = result
                time.sleep(0.5)
            if results:
                return self.combine_timeframe_results(results)
            return None
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None

    def analyze_timeframe(self, symbol, timeframe):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            if not ohlcv or len(ohlcv) < 20:
                return None
            df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
            df = self.calculate_indicators(df)
            signal = self.get_signal(df)
            return {"timeframe": timeframe, "signal": signal}
        except Exception as e:
            print(f"Error {symbol} {timeframe}: {e}")
            return None

    def calculate_indicators(self, df):
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df["rsi"] = 100 - (100 / (1 + gain / loss))
        exp1 = df["close"].ewm(span=12, adjust=False).mean()
        exp2 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = exp1 - exp2
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        return df

    def get_signal(self, df):
        try:
            rsi = df["rsi"].iloc[-1]
            macd = df["macd"].iloc[-1]
            ms = df["macd_signal"].iloc[-1]
            if rsi < 30 and macd > ms:
                return "STRONG_BUY"
            if rsi < 40 or (macd > ms and rsi < 50):
                return "BUY"
            if rsi > 70 and macd < ms:
                return "STRONG_SELL"
            if rsi > 60 or (macd < ms and rsi > 50):
                return "SELL"
            return "NEUTRAL"
        except:
            return "NEUTRAL"

    def combine_timeframe_results(self, results):
        try:
            signals = [d.get("signal","NEUTRAL") for d in results.values()]
            buys = sum(1 for s in signals if s in ["BUY","STRONG_BUY"])
            sells = sum(1 for s in signals if s in ["SELL","STRONG_SELL"])
            total = len(signals)
            if buys >= total * 0.6:
                sig = "BUY"
            elif sells >= total * 0.6:
                sig = "SELL"
            else:
                sig = "NEUTRAL"
            return {"signal": sig, "score": 50, "timeframe_signals": results}
        except Exception as e:
            return {"signal": "NEUTRAL", "score": 50, "timeframe_signals": results}

    def check_momentum_alignment(self, results):
        signals = [d.get("signal","NEUTRAL") for d in results.values()]
        buys = sum(1 for s in signals if s in ["BUY","STRONG_BUY"])
        sells = sum(1 for s in signals if s in ["SELL","STRONG_SELL"])
        total = len(signals)
        return (buys >= total * 0.6) or (sells >= total * 0.6)


def get_top_pairs(config=None, limit=50):
    try:
        from bot.config_loader import load_config
        from bot.exchange_factory import build_exchange
        from bot.market_scanner import MarketScanner
        if config is None:
            config = load_config()
        exchange = build_exchange(config)
        scanner = MarketScanner(config, exchange)
        pairs = scanner.scan_all_markets()
        if pairs:
            return pairs[:limit]
        return []
    except Exception as e:
        print(f"Error in get_top_pairs: {e}")
        return []

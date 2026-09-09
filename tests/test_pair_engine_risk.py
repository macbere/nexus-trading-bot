import unittest
from unittest.mock import patch
from types import SimpleNamespace

from bot.pair_engine import PairEngine
from bot.exchange_factory import get_positions
from bot.pair_trader import PairTrader


class PairEngineRiskTests(unittest.TestCase):
    @patch("bot.exchange_factory.get_balance")
    def test_session_loss_limit_latches(self, get_balance):
        get_balance.side_effect = [
            {"total": 100.0},
            {"total": 98.0},
            {"total": 99.5},
        ]
        engine = PairEngine({"BOT_MAX_DAILY_LOSS_USD": "2.0"})

        self.assertTrue(engine._loss_limit_ok())
        self.assertFalse(engine._loss_limit_ok())
        self.assertTrue(engine.risk_halted)
        self.assertFalse(engine._loss_limit_ok())

    @patch("bot.exchange_factory.get_balance", return_value={"total": 0})
    def test_unavailable_equity_fails_closed(self, get_balance):
        engine = PairEngine({"BOT_MAX_DAILY_LOSS_USD": "2.0"})

        self.assertFalse(engine._loss_limit_ok())
        self.assertIsNone(engine.session_equity)

    @patch("bot.exchange_factory.requests.get")
    def test_position_api_error_fails_closed(self, requests_get):
        requests_get.return_value = SimpleNamespace(
            status_code=400,
            json=lambda: {"code": "40010", "msg": "invalid account mode"},
        )

        self.assertIsNone(
            get_positions(
                {
                    "BITGET_API_KEY": "key",
                    "BITGET_SECRET": "secret",
                    "BITGET_PASSWORD": "pass",
                    "BITGET_DEMO": "true",
                },
                fail_closed=True,
            )
        )

    @patch("bot.exchange_factory._get_min_qty", return_value=0.1)
    @patch("bot.exchange_factory.get_balance", return_value={"free": 100.0})
    def test_quantity_skips_when_exchange_minimum_breaks_position_cap(
        self, get_balance, get_min_qty
    ):
        trader = PairTrader(
            "SOL/USDT:USDT",
            {"BOT_RISK_PCT": "10", "BOT_MAX_POS_USD": "3"},
        )

        self.assertEqual(trader._calc_qty(103.706), 0)

    @patch("bot.pair_trader.time.time", return_value=1000.0)
    @patch("bot.exchange_factory.place_order_direct", return_value={"orderId": "1"})
    @patch.object(PairTrader, "_calc_qty", return_value=1.0)
    @patch.object(PairTrader, "_get_price", return_value=100.0)
    def test_trade_passes_configured_exit_percentages(
        self, get_price, calc_qty, place_order, now
    ):
        trader = PairTrader(
            "BTC/USDT:USDT",
            {"MIN_TRADE_SCORE": "20", "BOT_TP_PCT": "2.5", "BOT_SL_PCT": "1.5"},
        )

        with patch("bot.exchange_factory.fetch_ohlcv_direct", return_value=[]):
            self.assertTrue(trader.trade_with_score(50, rsi=50))

        self.assertEqual(place_order.call_args.kwargs["tp_pct"], 0.025)
        self.assertEqual(place_order.call_args.kwargs["sl_pct"], 0.015)


if __name__ == "__main__":
    unittest.main()

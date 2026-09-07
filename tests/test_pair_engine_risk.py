import unittest
from unittest.mock import patch
from types import SimpleNamespace

from bot.pair_engine import PairEngine
from bot.exchange_factory import get_positions


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


if __name__ == "__main__":
    unittest.main()

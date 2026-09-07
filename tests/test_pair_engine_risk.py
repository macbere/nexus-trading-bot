import unittest
from unittest.mock import patch

from bot.pair_engine import PairEngine


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


if __name__ == "__main__":
    unittest.main()

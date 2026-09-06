import unittest

from bot.exchange_factory import _sign_request, is_demo_mode, place_order_direct


class ExchangeSafetyTests(unittest.TestCase):
    def test_demo_mode_is_the_default(self):
        self.assertTrue(is_demo_mode({}))
        self.assertTrue(is_demo_mode({"BITGET_DEMO": "true"}))
        self.assertFalse(is_demo_mode({"BITGET_DEMO": "false"}))

    def test_demo_requests_include_bitget_demo_header(self):
        headers = _sign_request(
            {
                "BITGET_API_KEY": "key",
                "BITGET_SECRET": "secret",
                "BITGET_PASSWORD": "pass",
                "BITGET_DEMO": "true",
            },
            "GET",
            "/api/v2/mix/account/account",
        )
        self.assertEqual(headers["paptrading"], "1")

    def test_live_orders_are_blocked_without_explicit_opt_in(self):
        with self.assertRaises(RuntimeError):
            place_order_direct(
                {"BITGET_DEMO": "false", "BOT_ALLOW_LIVE_TRADING": "false"},
                "BTC/USDT:USDT",
                "buy",
                1,
            )


if __name__ == "__main__":
    unittest.main()

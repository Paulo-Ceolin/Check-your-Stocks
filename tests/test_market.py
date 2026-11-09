import unittest
from unittest.mock import patch

from tracker.exceptions import MarketDataError
from tracker.market.service import get_price


class MarketServiceTests(unittest.TestCase):
    @patch("tracker.market.service._read_url", return_value='{"chart": {"result": [{"meta": {"regularMarketPrice": 50000}}]}}')
    def test_crypto_price(self, _read_url):
        price = get_price("BTC", "crypto")
        self.assertEqual(price.value, 50000)
        self.assertEqual(price.source, "Yahoo Finance")

    @patch("tracker.market.service._read_url", return_value='{"chart": {"result": [{"meta": {"regularMarketPrice": 150}}]}}')
    def test_stock_price(self, _read_url):
        price = get_price("AAPL", "stock")
        self.assertEqual(price.value, 150)
        self.assertEqual(price.source, "Yahoo Finance")

    @patch("tracker.market.service._read_url", return_value="not json")
    def test_bad_provider_response_is_reported(self, _read_url):
        with self.assertRaises(MarketDataError):
            get_price("BTC", "crypto")

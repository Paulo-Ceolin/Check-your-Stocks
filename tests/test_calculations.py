import unittest

from tracker.calculations import calculate_portfolio, calculate_position
from tracker.models import Asset, Holding


class CalculationTests(unittest.TestCase):
    def setUp(self):
        asset = Asset(1, "AAPL", "Apple", "stock")
        self.holding = Holding(1, 1, asset, 2, 100)

    def test_position_gain_and_return(self):
        result = calculate_position(self.holding, 125)
        self.assertEqual(result.market_value, 250)
        self.assertEqual(result.cost_basis, 200)
        self.assertEqual(result.profit_loss, 50)
        self.assertEqual(result.percent_return, 25)

    def test_portfolio_totals(self):
        positions, totals = calculate_portfolio([self.holding], {"AAPL": 125})
        self.assertEqual(len(positions), 1)
        self.assertEqual(totals.total_value, 250)
        self.assertEqual(totals.percent_return, 25)


import unittest

from tracker.exceptions import ValidationError
from tracker.validators import (
    validate_non_negative_number,
    validate_positive_number,
    validate_ticker,
)


class ValidatorTests(unittest.TestCase):
    def test_ticker_is_normalized(self):
        self.assertEqual(validate_ticker(" aapl "), "AAPL")

    def test_invalid_ticker_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_ticker("not a ticker!")

    def test_positive_number(self):
        self.assertEqual(validate_positive_number("1.5", "Quantity"), 1.5)
        with self.assertRaises(ValidationError):
            validate_positive_number("0", "Quantity")

    def test_non_negative_number_allows_zero(self):
        self.assertEqual(validate_non_negative_number("0", "Price"), 0)


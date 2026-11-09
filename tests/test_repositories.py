import sqlite3
import unittest

from tracker.database import SCHEMA
from tracker.models import Asset, Holding
from tracker.repositories import AssetRepository, HoldingRepository


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.execute("INSERT INTO portfolios (id, name) VALUES (1, 'Default')")
        self.assets = AssetRepository(self.connection)
        self.holdings = HoldingRepository(self.connection)

    def test_save_update_list_and_remove(self):
        asset = self.assets.get_or_create("BTC", "crypto", "Bitcoin", "bitcoin")
        self.holdings.save(Holding(None, 1, asset, 0.5, 40000))
        self.holdings.save(Holding(None, 1, asset, 0.75, 42000))
        stored = self.holdings.list()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].quantity, 0.75)
        self.assertTrue(self.holdings.remove("BTC"))
        self.assertEqual(self.holdings.list(), [])


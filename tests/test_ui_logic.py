import tempfile
import threading
import unittest
from pathlib import Path

from tracker.database import connect
from tracker.models import PositionResult
from ui.charts import allocation_percentages, cost_basis_series, format_gain_loss, sort_positions, value_series
from ui.app import create_worker_repositories
from ui.settings import MIN_REFRESH_INTERVAL_SECONDS, load_settings, save_settings


class UiLogicTests(unittest.TestCase):
    def test_allocation_percentages_sum_to_one_hundred(self):
        positions = [
            PositionResult("AAPL", 1, 100, 100, 80, 20, 25),
            PositionResult("BTC", 1, 200, 200, 150, 50, 33.333),
        ]
        allocations = allocation_percentages(positions)
        self.assertAlmostEqual(sum(value for _, value in allocations), 100)

    def test_chart_series_use_snapshot_values(self):
        rows = [
            {"taken_at": "2026-01-01", "total_value": 100, "total_cost": 80},
            {"taken_at": "2026-01-02", "total_value": 110, "total_cost": 80},
        ]
        self.assertEqual(value_series(rows)[1], ("2026-01-02", 110.0))
        self.assertEqual(cost_basis_series(rows)[0], ("2026-01-01", 80.0))

    def test_sort_positions(self):
        positions = [
            PositionResult("AAPL", 1, 100, 100, 80, 20, 25),
            PositionResult("BTC", 1, 200, 200, 150, 50, 33.333),
        ]
        self.assertEqual(sort_positions(positions)[0].ticker, "BTC")
        self.assertEqual(sort_positions(positions, "name")[0].ticker, "AAPL")

    def test_settings_are_validated_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_settings({"refresh_interval_seconds": 1, "theme": "invalid"}, path)
            settings = load_settings(path)
            self.assertEqual(settings["refresh_interval_seconds"], MIN_REFRESH_INTERVAL_SECONDS)
            self.assertEqual(settings["theme"], "dark")
            self.assertFalse(settings["widget_mode"])
            save_settings({"widget_mode": True}, path)
            self.assertTrue(load_settings(path)["widget_mode"])
            save_settings({"widget_mode": "yes"}, path)
            self.assertFalse(load_settings(path)["widget_mode"])

    def test_gain_loss_format(self):
        self.assertEqual(format_gain_loss(80.72), "+$80.72")
        self.assertEqual(format_gain_loss(-4.3), "-$4.30")

    def test_worker_uses_a_new_connection_from_another_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "portfolio.db"
            main_connection = connect(database_path)
            worker_result = []

            def run_worker_setup():
                connection, holdings, _ = create_worker_repositories(database_path)
                try:
                    worker_result.append((connection, holdings.list()))
                finally:
                    connection.close()

            thread = threading.Thread(target=run_worker_setup)
            thread.start()
            thread.join()

            self.assertEqual(len(worker_result), 1)
            worker_connection, holdings = worker_result[0]
            self.assertIsNot(worker_connection, main_connection)
            self.assertEqual(holdings, [])
            main_connection.close()

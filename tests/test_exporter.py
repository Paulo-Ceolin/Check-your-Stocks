import csv
import tempfile
import unittest
from pathlib import Path

from tracker.exporter import export_history


class ExporterTests(unittest.TestCase):
    def test_exports_history_csv(self):
        row = {
            "taken_at": "2026-01-01T00:00:00+00:00",
            "total_value": 120,
            "total_cost": 100,
            "profit_loss": 20,
            "percent_return": 20,
            "trigger": "manual",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = export_history([row], Path(directory) / "history.csv")
            with path.open(newline="", encoding="utf-8") as file:
                records = list(csv.reader(file))
        self.assertEqual(records[0][0], "taken_at")
        self.assertEqual(records[1][-1], "manual")


import csv
from pathlib import Path


def export_history(rows: list, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["taken_at", "total_value", "total_cost", "profit_loss", "percent_return", "trigger"]
        )
        for row in rows:
            writer.writerow(
                [row["taken_at"], row["total_value"], row["total_cost"],
                 row["profit_loss"], row["percent_return"], row["trigger"]]
            )
    return destination


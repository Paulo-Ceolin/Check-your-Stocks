import sqlite3

from .models import Asset, Holding, Price, PositionResult, PortfolioTotals, utc_now


class AssetRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_or_create(
        self, ticker: str, asset_type: str, name: str, provider_id: str | None = None
    ) -> Asset:
        row = self.connection.execute(
            "SELECT * FROM assets WHERE ticker = ?", (ticker,)
        ).fetchone()
        if row is None:
            cursor = self.connection.execute(
                "INSERT INTO assets (ticker, name, asset_type, provider_id) VALUES (?, ?, ?, ?)",
                (ticker, name, asset_type, provider_id),
            )
            self.connection.commit()
            return Asset(cursor.lastrowid, ticker, name, asset_type, provider_id)
        return Asset(row["id"], row["ticker"], row["name"], row["asset_type"], row["provider_id"])


class HoldingRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def save(self, holding: Holding) -> None:
        self.connection.execute(
            """
            INSERT INTO holdings (portfolio_id, asset_id, quantity, purchase_price, purchase_date)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (portfolio_id, asset_id) DO UPDATE SET
                quantity = excluded.quantity,
                purchase_price = excluded.purchase_price,
                purchase_date = excluded.purchase_date,
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            """,
            (
                holding.portfolio_id,
                holding.asset.id,
                holding.quantity,
                holding.purchase_price,
                holding.purchase_date,
            ),
        )
        self.connection.commit()

    def list(self, portfolio_id: int = 1) -> list[Holding]:
        rows = self.connection.execute(
            """
            SELECT h.*, a.ticker, a.name, a.asset_type, a.provider_id
            FROM holdings h JOIN assets a ON a.id = h.asset_id
            WHERE h.portfolio_id = ? ORDER BY a.ticker
            """,
            (portfolio_id,),
        ).fetchall()
        return [
            Holding(
                row["id"],
                row["portfolio_id"],
                Asset(row["asset_id"], row["ticker"], row["name"], row["asset_type"], row["provider_id"]),
                row["quantity"],
                row["purchase_price"],
                row["purchase_date"],
            )
            for row in rows
        ]

    def remove(self, ticker: str, portfolio_id: int = 1) -> bool:
        cursor = self.connection.execute(
            """
            DELETE FROM holdings WHERE portfolio_id = ?
            AND asset_id = (SELECT id FROM assets WHERE ticker = ?)
            """,
            (portfolio_id, ticker),
        )
        self.connection.commit()
        return cursor.rowcount > 0


class PriceRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def save(self, asset_id: int, price: Price) -> None:
        self.connection.execute(
            "INSERT INTO prices (asset_id, price, currency, source, retrieved_at) VALUES (?, ?, ?, ?, ?)",
            (asset_id, price.value, price.currency, price.source, price.retrieved_at),
        )
        self.connection.commit()


class SnapshotRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def save(
        self,
        portfolio_id: int,
        totals: PortfolioTotals,
        positions: list[PositionResult],
        asset_ids: dict[str, int],
        trigger: str,
    ) -> None:
        timestamp = utc_now()
        cursor = self.connection.execute(
            """
            INSERT INTO portfolio_snapshots
            (portfolio_id, taken_at, total_value, total_cost, profit_loss, percent_return, trigger)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (portfolio_id, timestamp, totals.total_value, totals.total_cost,
             totals.profit_loss, totals.percent_return, trigger),
        )
        for position in positions:
            self.connection.execute(
                """
                INSERT INTO snapshot_positions
                (snapshot_id, asset_id, quantity, price, market_value, cost_basis)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cursor.lastrowid, asset_ids[position.ticker], position.quantity,
                 position.price, position.market_value, position.cost_basis),
            )
        self.connection.commit()

    def history(self, portfolio_id: int = 1) -> list[sqlite3.Row]:
        return self.connection.execute(
            "SELECT * FROM portfolio_snapshots WHERE portfolio_id = ? ORDER BY taken_at DESC",
            (portfolio_id,),
        ).fetchall()


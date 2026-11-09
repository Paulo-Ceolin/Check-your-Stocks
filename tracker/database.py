import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL DEFAULT 'Default',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    ticker TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('stock', 'etf', 'crypto')),
    provider_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    quantity REAL NOT NULL CHECK (quantity > 0),
    purchase_price REAL NOT NULL CHECK (purchase_price >= 0),
    purchase_date TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (portfolio_id, asset_id)
);
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    price REAL NOT NULL CHECK (price >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    source TEXT NOT NULL,
    retrieved_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prices_asset_time ON prices (asset_id, retrieved_at DESC);
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    taken_at TEXT NOT NULL,
    total_value REAL NOT NULL,
    total_cost REAL NOT NULL,
    profit_loss REAL NOT NULL,
    percent_return REAL NOT NULL,
    trigger TEXT NOT NULL CHECK (trigger IN ('manual', 'refresh'))
);
CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio_time
    ON portfolio_snapshots (portfolio_id, taken_at);
CREATE TABLE IF NOT EXISTS snapshot_positions (
    snapshot_id INTEGER NOT NULL REFERENCES portfolio_snapshots(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    market_value REAL NOT NULL,
    cost_basis REAL NOT NULL,
    PRIMARY KEY (snapshot_id, asset_id)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    connection.execute(
        "INSERT OR IGNORE INTO portfolios (id, name) VALUES (1, 'Default')"
    )
    connection.commit()
    return connection


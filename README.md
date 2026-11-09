# Crypto & Stock Portfolio Tracker

A free, Python standard-library CLI for tracking stocks, ETFs, and cryptocurrencies.

## Free market data

- **Stocks, ETFs, and cryptocurrencies:** Yahoo Finance's public chart endpoint; no API key.

Public services can rate-limit requests. The application reports provider errors instead of hiding them.

## Run

Requires Python 3.11+ and internet access for price refreshes.

```powershell
python main.py
```

The SQLite database is created at `data/portfolio.db`; exports are written to
`data/exports/portfolio_history.csv`. Both are ignored by Git.

The current release is documented in [VERSION.md](VERSION.md).

## Desktop widget (Version 0.2)

Install the optional UI dependencies and launch the widget:

```powershell
python -m pip install -r requirements.txt
python main.py --gui
```

The widget uses the same Yahoo Finance public chart endpoint as the terminal
app and does not require an API key. It stores UI overrides in
`data/settings.json`. The default chart shows saved portfolio history; use
**Save snapshot** to begin tracking it. If fewer than two snapshots exist, the
chart displays an empty-state message.

The widget is a wide dark finance dashboard (minimum 1000 x 640) with summary
cards, an aligned holdings table, side-by-side value-history and allocation
charts, refresh status, and footer actions for managing holdings, snapshots,
and CSV export.

![Version 0.2 desktop widget screenshot placeholder](docs/widget-screenshot.png)

## Development

There are no third-party runtime dependencies. The calculation, validation,
database, and export layers are intentionally separated so they can be tested
without calling live market APIs.

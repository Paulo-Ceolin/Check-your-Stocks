# Version 0.1

## Capabilities

- Track stocks, ETFs, and cryptocurrencies.
- Add or update holdings with ticker, asset type, quantity, purchase price,
  and an optional asset name.
- Remove holdings by ticker.
- View the portfolio with live Yahoo Finance prices.
- Calculate total value, total cost, gain or loss, and percentage return.
- Refresh prices and save portfolio snapshots.
- Export snapshot history to
  `data/exports/portfolio_history.csv`.
- Store portfolio data locally in SQLite at `data/portfolio.db`.
- Report market-data and validation errors without hiding them.

## Appearance

Version 0.1 is a terminal-based application. When launched, it displays the
title **Crypto & Stock Portfolio Tracker**, followed by a numbered menu:

```text
1) View portfolio  2) Add/update holding  3) Remove holding
4) Refresh prices  5) Save snapshot  6) Export history  0) Exit
```

The portfolio view uses a table with these columns:

```text
Ticker   Qty          Price        Value        Gain/Loss
```

It also displays total value, total cost, total return, and percentage return.

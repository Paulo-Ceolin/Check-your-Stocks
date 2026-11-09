from pathlib import Path

from config import DATABASE_PATH, EXPORT_DIR
from .calculations import calculate_portfolio
from .database import connect
from .exceptions import TrackerError
from .exporter import export_history
from .market.service import get_price
from .portfolio import PortfolioManager
from .repositories import AssetRepository, HoldingRepository, PriceRepository, SnapshotRepository


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _display(holdings, prices) -> tuple[list, object]:
    positions, totals = calculate_portfolio(holdings, prices)
    print("\nTicker   Qty          Price        Value        Gain/Loss")
    print("-" * 60)
    for position in positions:
        print(
            f"{position.ticker:<8}{position.quantity:<12.6g}"
            f"{_money(position.price):<13}{_money(position.market_value):<13}"
            f"{_money(position.profit_loss)}"
        )
    print(f"\nTotal value: {_money(totals.total_value)}")
    print(f"Total cost:  {_money(totals.total_cost)}")
    print(f"Return:      {_money(totals.profit_loss)} ({totals.percent_return:.2f}%)")
    return positions, totals


def run() -> None:
    connection = connect(DATABASE_PATH)
    holdings = HoldingRepository(connection)
    assets = AssetRepository(connection)
    prices = PriceRepository(connection)
    snapshots = SnapshotRepository(connection)
    manager = PortfolioManager(assets, holdings)
    print("Crypto & Stock Portfolio Tracker")
    while True:
        print("\n1) View portfolio  2) Add/update holding  3) Remove holding")
        print("4) Refresh prices  5) Save snapshot  6) Export history  0) Exit")
        choice = input("Choose an option: ").strip()
        try:
            if choice == "0":
                break
            if choice == "1":
                current = holdings.list()
                if not current:
                    print("No holdings yet.")
                    continue
                fetched = {h.asset.ticker: get_price(h.asset.ticker, h.asset.asset_type).value for h in current}
                _display(current, fetched)
            elif choice == "2":
                manager.add_or_update(
                    input("Ticker: "),
                    input("Type (stock/etf/crypto): ").strip().lower(),
                    input("Quantity: "),
                    input("Purchase price per unit: "),
                    input("Asset name (optional): "),
                )
                print("Holding saved.")
            elif choice == "3":
                print("Removed." if manager.remove(input("Ticker: ")) else "Holding not found.")
            elif choice in {"4", "5"}:
                current = holdings.list()
                if not current:
                    print("No holdings yet.")
                    continue
                fetched = {}
                for holding in current:
                    price = get_price(holding.asset.ticker, holding.asset.asset_type)
                    fetched[holding.asset.ticker] = price.value
                    prices.save(holding.asset.id, price)
                position_list, totals = _display(current, fetched)
                asset_ids = {h.asset.ticker: h.asset.id for h in current}
                snapshots.save(1, totals, position_list, asset_ids, "refresh" if choice == "4" else "manual")
                print("Snapshot saved.")
            elif choice == "6":
                path = export_history(snapshots.history(), Path(EXPORT_DIR) / "portfolio_history.csv")
                print(f"Exported to {path}")
            else:
                print("Please choose a listed option.")
        except TrackerError as exc:
            print(f"Error: {exc}")
        except KeyboardInterrupt:
            print("\nExiting.")
            break
    connection.close()


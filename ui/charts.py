from collections.abc import Iterable, Mapping

from tracker.models import PositionResult


def format_gain_loss(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):,.2f}"


def value_series(snapshots: Iterable[Mapping]) -> list[tuple[str, float]]:
    return [(row["taken_at"], float(row["total_value"])) for row in snapshots]


def cost_basis_series(snapshots: Iterable[Mapping]) -> list[tuple[str, float]]:
    return [(row["taken_at"], float(row["total_cost"])) for row in snapshots]


def allocation_percentages(
    positions: Iterable[PositionResult],
) -> list[tuple[str, float]]:
    position_list = list(positions)
    total = sum(position.market_value for position in position_list)
    if total <= 0:
        return [(position.ticker, 0.0) for position in position_list]
    return [
        (position.ticker, position.market_value / total * 100)
        for position in position_list
    ]


def sort_positions(
    positions: Iterable[PositionResult], sort_by: str = "value"
) -> list[PositionResult]:
    keys = {
        "value": lambda position: position.market_value,
        "gain_loss": lambda position: position.profit_loss,
        "name": lambda position: position.ticker,
    }
    return sorted(positions, key=keys.get(sort_by, keys["value"]), reverse=sort_by != "name")

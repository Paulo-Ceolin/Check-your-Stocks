from collections.abc import Iterable, Mapping
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from tracker.models import PositionResult

CHART_PERIODS = ("Today", "Last 7 days", "Last 30 days")
CHICAGO = ZoneInfo("America/Chicago")


def format_gain_loss(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):,.2f}"


def value_series(snapshots: Iterable[Mapping]) -> list[tuple[str, float]]:
    return [(row["taken_at"], float(row["total_value"])) for row in snapshots]


def cost_basis_series(snapshots: Iterable[Mapping]) -> list[tuple[str, float]]:
    return [(row["taken_at"], float(row["total_cost"])) for row in snapshots]


def filter_series_by_period(
    snapshots: Iterable[Mapping], period: str, now: datetime
) -> list[Mapping]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now_utc = now.astimezone(timezone.utc)
    if period == "Today":
        local_midnight = datetime.combine(
            now_utc.astimezone(CHICAGO).date(), time.min, tzinfo=CHICAGO
        )
        cutoff = local_midnight.astimezone(timezone.utc)
    elif period == "Last 7 days":
        cutoff = now_utc - timedelta(days=7)
    elif period == "Last 30 days":
        cutoff = now_utc - timedelta(days=30)
    else:
        raise ValueError(f"Unknown chart period: {period}")

    filtered = []
    for snapshot in snapshots:
        taken_at = datetime.fromisoformat(str(snapshot["taken_at"]).replace("Z", "+00:00"))
        if taken_at.tzinfo is None:
            taken_at = taken_at.replace(tzinfo=timezone.utc)
        if taken_at.astimezone(timezone.utc) >= cutoff:
            filtered.append(snapshot)
    return filtered


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

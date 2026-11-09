from collections.abc import Iterable, Mapping

from .models import Holding, PortfolioTotals, PositionResult


def calculate_position(holding: Holding, current_price: float) -> PositionResult:
    cost_basis = holding.quantity * holding.purchase_price
    market_value = holding.quantity * current_price
    profit_loss = market_value - cost_basis
    percent_return = (profit_loss / cost_basis * 100) if cost_basis else 0.0
    return PositionResult(
        holding.asset.ticker,
        holding.quantity,
        current_price,
        market_value,
        cost_basis,
        profit_loss,
        percent_return,
    )


def calculate_totals(positions: Iterable[PositionResult]) -> PortfolioTotals:
    position_list = list(positions)
    total_value = sum(position.market_value for position in position_list)
    total_cost = sum(position.cost_basis for position in position_list)
    profit_loss = total_value - total_cost
    percent_return = (profit_loss / total_cost * 100) if total_cost else 0.0
    return PortfolioTotals(total_value, total_cost, profit_loss, percent_return)


def calculate_portfolio(
    holdings: Iterable[Holding], prices: Mapping[str, float]
) -> tuple[list[PositionResult], PortfolioTotals]:
    positions = [
        calculate_position(holding, prices[holding.asset.ticker])
        for holding in holdings
    ]
    return positions, calculate_totals(positions)


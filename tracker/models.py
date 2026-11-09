from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Asset:
    id: int | None
    ticker: str
    name: str
    asset_type: str
    provider_id: str | None = None


@dataclass(frozen=True)
class Holding:
    id: int | None
    portfolio_id: int
    asset: Asset
    quantity: float
    purchase_price: float
    purchase_date: str | None = None


@dataclass(frozen=True)
class Price:
    ticker: str
    value: float
    currency: str
    source: str
    retrieved_at: str


@dataclass(frozen=True)
class PositionResult:
    ticker: str
    quantity: float
    price: float
    market_value: float
    cost_basis: float
    profit_loss: float
    percent_return: float


@dataclass(frozen=True)
class PortfolioTotals:
    total_value: float
    total_cost: float
    profit_loss: float
    percent_return: float


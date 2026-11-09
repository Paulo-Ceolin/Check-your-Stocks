from .exceptions import ValidationError
from .models import Holding
from .repositories import AssetRepository, HoldingRepository
from .validators import validate_non_negative_number, validate_positive_number, validate_ticker


class PortfolioManager:
    def __init__(self, asset_repo: AssetRepository, holding_repo: HoldingRepository):
        self.asset_repo = asset_repo
        self.holding_repo = holding_repo

    def add_or_update(
        self,
        ticker_input: str,
        asset_type: str,
        quantity_input: str,
        purchase_price_input: str,
        name: str = "",
        provider_id: str | None = None,
        purchase_date: str | None = None,
    ) -> None:
        ticker = validate_ticker(ticker_input)
        if asset_type not in {"stock", "etf", "crypto"}:
            raise ValidationError("Asset type must be stock, etf, or crypto.")
        quantity = validate_positive_number(quantity_input, "Quantity")
        purchase_price = validate_non_negative_number(purchase_price_input, "Purchase price")
        asset = self.asset_repo.get_or_create(
            ticker, asset_type, name.strip() or ticker, provider_id
        )
        self.holding_repo.save(Holding(None, 1, asset, quantity, purchase_price, purchase_date))

    def remove(self, ticker_input: str) -> bool:
        return self.holding_repo.remove(validate_ticker(ticker_input))


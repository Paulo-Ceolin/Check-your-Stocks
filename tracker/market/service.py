import json
import urllib.error
import urllib.parse
import urllib.request

from ..exceptions import MarketDataError
from ..models import Price, utc_now

def _read_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "portfolio-tracker/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise MarketDataError(f"Could not retrieve market data: {exc}") from exc


def get_price(ticker: str, asset_type: str) -> Price:
    symbol = f"{ticker.upper()}-USD" if asset_type == "crypto" else ticker.upper()
    query = urllib.parse.urlencode({"range": "1d", "interval": "1d"})
    try:
        payload = json.loads(
            _read_url(
                f"https://query1.finance.yahoo.com/v8/finance/chart/"
                f"{urllib.parse.quote(symbol)}?{query}"
            )
        )
    except json.JSONDecodeError as exc:
        raise MarketDataError(
            f"Yahoo Finance returned an invalid response for {ticker}."
        ) from exc
    result = (payload.get("chart", {}).get("result") or [None])[0]
    value = result.get("meta", {}).get("regularMarketPrice") if result else None
    source = "Yahoo Finance"
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise MarketDataError(f"No USD price was found for {ticker}.") from exc
    if numeric_value < 0:
        raise MarketDataError(f"Provider returned an invalid price for {ticker}.")
    return Price(ticker, numeric_value, "USD", source, utc_now())

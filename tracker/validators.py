import re

from .exceptions import ValidationError

TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,9}$")


def validate_ticker(value: str) -> str:
    ticker = value.strip().upper()
    if not TICKER_PATTERN.fullmatch(ticker):
        raise ValidationError("Ticker must be 1-10 letters, numbers, dots, or hyphens.")
    return ticker


def validate_positive_number(value: str, field_name: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a number.") from exc
    if number <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return number


def validate_non_negative_number(value: str, field_name: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a number.") from exc
    if number < 0:
        raise ValidationError(f"{field_name} cannot be negative.")
    return number


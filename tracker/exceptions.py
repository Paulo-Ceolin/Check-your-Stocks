class TrackerError(Exception):
    """Base exception for expected application errors."""


class ValidationError(TrackerError):
    pass


class MarketDataError(TrackerError):
    pass


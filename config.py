from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "portfolio.db"
EXPORT_DIR = DATA_DIR / "exports"
SETTINGS_PATH = DATA_DIR / "settings.json"
HTTP_TIMEOUT_SECONDS = 10

DEFAULT_SETTINGS = {
    "auto_refresh": False,
    "refresh_interval_seconds": 300,
    "save_snapshot_on_refresh": False,
    "theme": "dark",
    "default_chart": "value",
    "always_on_top": False,
}

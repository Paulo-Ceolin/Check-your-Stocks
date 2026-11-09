import json
from copy import deepcopy
from pathlib import Path

from config import DEFAULT_SETTINGS, SETTINGS_PATH

MIN_REFRESH_INTERVAL_SECONDS = 60
VALID_THEMES = {"dark", "light"}
VALID_CHARTS = {"value", "allocation"}


def validate_settings(values: dict) -> dict:
    result = deepcopy(DEFAULT_SETTINGS)
    result["widget_mode"] = False
    if not isinstance(values, dict):
        return result
    if isinstance(values.get("auto_refresh"), bool):
        result["auto_refresh"] = values["auto_refresh"]
    interval = values.get("refresh_interval_seconds")
    if isinstance(interval, (int, float)) and not isinstance(interval, bool):
        result["refresh_interval_seconds"] = max(
            MIN_REFRESH_INTERVAL_SECONDS, int(interval)
        )
    if isinstance(values.get("save_snapshot_on_refresh"), bool):
        result["save_snapshot_on_refresh"] = values["save_snapshot_on_refresh"]
    if values.get("theme") in VALID_THEMES:
        result["theme"] = values["theme"]
    if values.get("default_chart") in VALID_CHARTS:
        result["default_chart"] = values["default_chart"]
    if isinstance(values.get("always_on_top"), bool):
        result["always_on_top"] = values["always_on_top"]
    if isinstance(values.get("widget_mode"), bool):
        result["widget_mode"] = values["widget_mode"]
    return result


def load_settings(path: Path = SETTINGS_PATH) -> dict:
    try:
        with path.open(encoding="utf-8") as file:
            return validate_settings(json.load(file))
    except (OSError, json.JSONDecodeError):
        return validate_settings({})


def save_settings(values: dict, path: Path = SETTINGS_PATH) -> dict:
    settings = validate_settings(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(settings, file, indent=2)
        file.write("\n")
    return settings

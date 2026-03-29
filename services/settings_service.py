import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppSettings:
    default_output_dir: str = ""
    max_workers: int = 2
    naming_strategy: str = "auto_increment"
    open_output_dir_after_completion: bool = False


class SettingsService:
    SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"
    _cache: AppSettings | None = None

    @classmethod
    def load(cls) -> AppSettings:
        if cls._cache is not None:
            return cls._cache

        if not cls.SETTINGS_FILE.exists():
            cls._cache = AppSettings()
            return cls._cache

        try:
            raw_data = json.loads(cls.SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cls._cache = AppSettings()
            return cls._cache

        valid_keys = {field.name for field in AppSettings.__dataclass_fields__.values()}
        filtered = {key: value for key, value in raw_data.items() if key in valid_keys}
        settings = AppSettings(**filtered)
        settings.max_workers = max(1, min(4, int(settings.max_workers or 2)))
        cls._cache = settings
        return settings

    @classmethod
    def save(cls, settings: AppSettings) -> None:
        settings.max_workers = max(1, min(4, int(settings.max_workers or 2)))
        cls.SETTINGS_FILE.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        cls._cache = settings

    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache = None

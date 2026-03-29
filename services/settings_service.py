import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def get_max_worker_limit() -> int:
    return max(1, os.cpu_count() or 1)


def get_default_worker_count() -> int:
    return min(4, get_max_worker_limit())


@dataclass
class AppSettings:
    default_output_dir: str = ""
    max_workers: int = get_default_worker_count()
    naming_strategy: str = "auto_increment"
    open_output_dir_after_completion: bool = False


class SettingsService:
    SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"
    _cache: AppSettings | None = None

    @classmethod
    def _normalize_max_workers(cls, value: int | None) -> int:
        return max(1, min(get_max_worker_limit(), int(value or get_default_worker_count())))

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
        settings.max_workers = cls._normalize_max_workers(settings.max_workers)
        cls._cache = settings
        return settings

    @classmethod
    def save(cls, settings: AppSettings) -> None:
        settings.max_workers = cls._normalize_max_workers(settings.max_workers)
        cls.SETTINGS_FILE.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        cls._cache = settings

    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache = None

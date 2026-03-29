import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from services.settings_service import SettingsService


def get_app_base_dir() -> Path:
    """Return the base directory for bundled and development runs."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def get_resource_base_dir() -> Path:
    """Return the base directory for bundled resources."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    return get_app_base_dir()


def get_resource_path(relative_path: str) -> str:
    """Get an absolute resource path for development and bundled runs."""
    return str(get_resource_base_dir() / relative_path)


def _resolve_binary(candidate: Optional[str]) -> Optional[str]:
    if not candidate:
        return None

    resolved = shutil.which(candidate) or candidate
    path = Path(resolved)
    return str(path.resolve()) if path.exists() else None


def _find_in_local_ffmpeg(binary_name: str) -> Optional[str]:
    search_roots = [get_app_base_dir()]

    resource_root = get_resource_base_dir()
    if resource_root not in search_roots:
        search_roots.append(resource_root)

    for root in search_roots:
        candidate = root / "ffmpeg" / binary_name
        if candidate.exists():
            return str(candidate.resolve())

    return None


def _find_in_custom_ffmpeg_dir(binary_name: str) -> Optional[str]:
    custom_dir = SettingsService.load().custom_ffmpeg_dir.strip()
    if not custom_dir:
        return None

    candidate = Path(custom_dir) / binary_name
    if candidate.exists():
        return str(candidate.resolve())

    return None


def find_ffmpeg_executable() -> Optional[str]:
    """Find ffmpeg.exe or ffmpeg in PATH/local ffmpeg directory."""
    return (
        _find_in_custom_ffmpeg_dir("ffmpeg.exe")
        or _find_in_custom_ffmpeg_dir("ffmpeg")
        or _resolve_binary("ffmpeg.exe")
        or _resolve_binary("ffmpeg")
        or _find_in_local_ffmpeg("ffmpeg.exe")
    )


def find_ffprobe_executable() -> Optional[str]:
    """Find ffprobe.exe or ffprobe in PATH/local ffmpeg directory."""
    return (
        _find_in_custom_ffmpeg_dir("ffprobe.exe")
        or _find_in_custom_ffmpeg_dir("ffprobe")
        or _resolve_binary("ffprobe.exe")
        or _resolve_binary("ffprobe")
        or _find_in_local_ffmpeg("ffprobe.exe")
    )

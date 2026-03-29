import json
import os
import subprocess
from typing import Any, Dict, Optional

from utils.logging_utils import get_logger
from utils.path_utils import find_ffmpeg_executable, find_ffprobe_executable

logger = get_logger(__name__)


class FFmpegService:
    @staticmethod
    def _hidden_process_kwargs() -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if os.name != "nt":
            return kwargs

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if creationflags:
            kwargs["creationflags"] = creationflags

        startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)
        use_show_window = getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        if startupinfo_factory and use_show_window:
            startupinfo = startupinfo_factory()
            startupinfo.dwFlags |= use_show_window
            kwargs["startupinfo"] = startupinfo

        return kwargs

    @staticmethod
    def get_ffprobe_path() -> Optional[str]:
        return find_ffprobe_executable()

    @staticmethod
    def get_ffmpeg_path() -> Optional[str]:
        return find_ffmpeg_executable()

    @staticmethod
    def get_availability_error() -> Optional[str]:
        ffprobe_path = FFmpegService.get_ffprobe_path()
        ffmpeg_path = FFmpegService.get_ffmpeg_path()

        if not ffprobe_path and not ffmpeg_path:
            return "未找到 ffmpeg 和 ffprobe，请检查程序目录或系统环境。"
        if not ffprobe_path:
            return "未找到 ffprobe，无法读取媒体信息。"
        if not ffmpeg_path:
            return "未找到 ffmpeg，无法执行转换。"
        return None

    @staticmethod
    def get_file_info(filepath: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(filepath):
            return None

        ffprobe_path = FFmpegService.get_ffprobe_path()
        if not ffprobe_path:
            logger.error("未找到 ffprobe，无法读取文件信息: %s", filepath)
            return None

        cmd = [
            ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            filepath,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                **FFmpegService._hidden_process_kwargs(),
            )
            if result.returncode != 0:
                logger.error("ffprobe 执行失败: %s", result.stderr.strip())
                return None

            data = json.loads(result.stdout)
            return FFmpegService._parse_file_info(data)
        except FileNotFoundError:
            logger.exception("ffprobe 可执行文件不存在")
            return None
        except json.JSONDecodeError as exc:
            logger.exception("ffprobe JSON 解析失败: %s", exc)
            return None
        except Exception as exc:
            logger.exception("获取文件信息时出错: %s", exc)
            return None

    @staticmethod
    def _parse_file_info(data: Dict[str, Any]) -> Dict[str, Any]:
        info = {
            "duration": None,
            "size": None,
            "audio_format": None,
            "video_format": None,
            "bit_rate": None,
            "sample_rate": None,
            "channels": None,
            "resolution": None,
            "fps": None,
        }

        format_info = data.get("format", {})
        info["duration"] = float(format_info.get("duration", 0)) if format_info.get("duration") else None
        info["size"] = int(format_info.get("size", 0)) if format_info.get("size") else None

        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type")
            if codec_type == "audio":
                info["audio_format"] = stream.get("codec_name")
                info["sample_rate"] = int(stream.get("sample_rate", 0)) if stream.get("sample_rate") else None
                info["channels"] = int(stream.get("channels", 0)) if stream.get("channels") else None
                if stream.get("bit_rate"):
                    info["bit_rate"] = int(stream["bit_rate"])
            elif codec_type == "video":
                info["video_format"] = stream.get("codec_name")
                width = stream.get("width")
                height = stream.get("height")
                if width and height:
                    info["resolution"] = f"{width}x{height}"

                frame_rate = stream.get("r_frame_rate", "")
                if "/" in frame_rate:
                    try:
                        numerator, denominator = frame_rate.split("/")
                        fps = float(numerator) / float(denominator)
                        info["fps"] = round(fps, 2) if fps else None
                    except (ValueError, ZeroDivisionError):
                        info["fps"] = None

        return info

    @staticmethod
    def check_ffmpeg_available() -> bool:
        if FFmpegService.get_availability_error():
            return False

        ffprobe_path = FFmpegService.get_ffprobe_path()
        ffmpeg_path = FFmpegService.get_ffmpeg_path()
        try:
            subprocess.run(
                [ffprobe_path, "-version"],
                capture_output=True,
                check=True,
                **FFmpegService._hidden_process_kwargs(),
            )
            subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                check=True,
                **FFmpegService._hidden_process_kwargs(),
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

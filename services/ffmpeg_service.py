import json
import os
import subprocess
from typing import Any, Dict, Optional

from utils.logging_utils import get_logger
from utils.path_utils import find_ffmpeg_executable, find_ffprobe_executable

logger = get_logger(__name__)


class FFmpegService:
    """Read media metadata through ffprobe and resolve FFmpeg binaries."""

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
            return "??? ffmpeg ? ffprobe???? FFmpeg ?? ffmpeg ????????????"
        if not ffprobe_path:
            return "??? ffprobe????????????? FFmpeg ???????"
        if not ffmpeg_path:
            return "??? ffmpeg??????????? FFmpeg ???????"
        return None

    @staticmethod
    def get_file_info(filepath: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(filepath):
            return None

        ffprobe_path = FFmpegService.get_ffprobe_path()
        if not ffprobe_path:
            logger.error("??? ffprobe?????????: %s", filepath)
            return None

        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            filepath,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
            )
            if result.returncode != 0:
                logger.error("ffprobe ????: %s", result.stderr.strip())
                return None

            data = json.loads(result.stdout)
            return FFmpegService._parse_file_info(data)
        except FileNotFoundError:
            logger.exception("ffprobe ????????")
            return None
        except json.JSONDecodeError as exc:
            logger.exception("ffprobe JSON ????: %s", exc)
            return None
        except Exception as exc:
            logger.exception("?????????: %s", exc)
            return None

    @staticmethod
    def _parse_file_info(data: Dict[str, Any]) -> Dict[str, Any]:
        info = {
            'duration': None,
            'size': None,
            'audio_format': None,
            'video_format': None,
            'bit_rate': None,
            'sample_rate': None,
            'channels': None,
            'resolution': None,
            'fps': None,
        }

        format_info = data.get('format', {})
        info['duration'] = float(format_info.get('duration', 0)) if format_info.get('duration') else None
        info['size'] = int(format_info.get('size', 0)) if format_info.get('size') else None

        for stream in data.get('streams', []):
            codec_type = stream.get('codec_type')
            if codec_type == 'audio':
                info['audio_format'] = stream.get('codec_name')
                info['sample_rate'] = int(stream.get('sample_rate', 0)) if stream.get('sample_rate') else None
                info['channels'] = int(stream.get('channels', 0)) if stream.get('channels') else None
                if stream.get('bit_rate'):
                    info['bit_rate'] = int(stream['bit_rate'])
            elif codec_type == 'video':
                info['video_format'] = stream.get('codec_name')
                width = stream.get('width')
                height = stream.get('height')
                if width and height:
                    info['resolution'] = f"{width}x{height}"

                frame_rate = stream.get('r_frame_rate', '')
                if '/' in frame_rate:
                    try:
                        numerator, denominator = frame_rate.split('/')
                        fps = float(numerator) / float(denominator)
                        info['fps'] = round(fps, 2) if fps else None
                    except (ValueError, ZeroDivisionError):
                        info['fps'] = None

        return info

    @staticmethod
    def check_ffmpeg_available() -> bool:
        if FFmpegService.get_availability_error():
            return False

        ffprobe_path = FFmpegService.get_ffprobe_path()
        ffmpeg_path = FFmpegService.get_ffmpeg_path()
        try:
            subprocess.run([ffprobe_path, '-version'], capture_output=True, check=True)
            subprocess.run([ffmpeg_path, '-version'], capture_output=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

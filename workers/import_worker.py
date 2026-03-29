import os
from typing import List

from PyQt6.QtCore import QObject, pyqtSignal

from models import FileInfo
from services.ffmpeg_service import FFmpegService
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class ImportWorker(QObject):
    progress_updated = pyqtSignal(int, int, str)
    file_loaded = pyqtSignal(object)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, input_files: List[str]):
        super().__init__()
        self.input_files = input_files

    def run(self):
        total_files = len(self.input_files)
        try:
            for index, path in enumerate(self.input_files, start=1):
                self.progress_updated.emit(index, total_files, os.path.basename(path))

                info = FileInfo(
                    filepath=os.path.abspath(path),
                    filename=os.path.basename(path),
                )
                media_info = FFmpegService.get_file_info(path)
                if media_info:
                    info.duration = media_info.get("duration")
                    info.size = media_info.get("size")
                    info.audio_format = media_info.get("audio_format")
                    info.video_format = media_info.get("video_format")
                    info.bit_rate = media_info.get("bit_rate")
                    info.sample_rate = media_info.get("sample_rate")
                    info.channels = media_info.get("channels")
                    info.resolution = media_info.get("resolution")
                    info.fps = media_info.get("fps")

                self.file_loaded.emit(info)

            self.finished.emit()
        except Exception as exc:
            logger.exception("导入文件信息时出错")
            self.error.emit(f"导入文件信息时出错: {exc}")

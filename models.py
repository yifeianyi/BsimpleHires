from dataclasses import dataclass
import os

@dataclass
class FileInfo:
    filepath: str
    filename: str
    duration: float | None = None   # 秒
    size: int | None = None         # 字节
    audio_format: str | None = None # PCM/AAC/FLAC/...
    video_format: str | None = None # H.264/H.265/AV1/...
    bit_rate: int | None = None     # 比特率 bps
    sample_rate: int | None = None  # 采样率 Hz
    channels: int | None = None     # 声道数
    resolution: str | None = None   # 分辨率 1920x1080
    fps: float | None = None        # 帧率
    selected: bool = True

class FileManager:
    """管理文件数据，不依赖 UI"""
    def __init__(self):
        self.files: list[FileInfo] = []

    def add_file(self, path: str):
        info = FileInfo(
            filepath=path,
            filename=os.path.basename(path)
        )
        self.files.append(info)
        return info

    def get_all(self):
        return self.files
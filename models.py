from dataclasses import dataclass
import os

@dataclass
class FileInfo:
    filepath: str
    filename: str
    duration: float | None = None   # 秒
    size: int | None = None         # 字节
    audio_format: str | None = None # PCM/AAC/FLAC/...
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
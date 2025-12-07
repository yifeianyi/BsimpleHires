from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QFileDialog, QTableWidgetItem,
    QCheckBox, QHBoxLayout, QWidget
)
from PyQt6.QtCore import Qt

from models import FileInfo, FileManager
from services.ffmpeg_service import FFmpegService


class WorkPage(QWidget):

    # ======================================================
    # 列定义（结构化方案）
    # ======================================================
    COLS = {
        "check":     {"index": 0, "title": "全选",      "align": Qt.AlignmentFlag.AlignCenter},
        "name":      {"index": 1, "title": "文件名",    "align": Qt.AlignmentFlag.AlignLeft},
        "duration":  {"index": 2, "title": "时长",     "align": Qt.AlignmentFlag.AlignCenter},
        "size":      {"index": 3, "title": "大小",      "align": Qt.AlignmentFlag.AlignRight},
        "resolution":{"index": 4, "title": "分辨率",    "align": Qt.AlignmentFlag.AlignCenter},
        "fps":       {"index": 5, "title": "帧率",      "align": Qt.AlignmentFlag.AlignCenter},
        "vformat":   {"index": 6, "title": "视频格式",  "align": Qt.AlignmentFlag.AlignCenter},
        "aformat":   {"index": 7, "title": "音频格式",  "align": Qt.AlignmentFlag.AlignCenter},
        "path":      {"index": 8, "title": "位置",      "align": Qt.AlignmentFlag.AlignLeft},
    }

    def __init__(self):
        super().__init__()
        uic.loadUi("ui/workPage.ui", self)

        # 后端数据管理器
        self.fileManager = FileManager()

        # 检查ffmpeg是否可用
        if not FFmpegService.check_ffmpeg_available():
            print("警告: 未检测到ffmpeg/ffprobe，无法读取媒体文件信息")

        # UI 按钮
        self.ImportButton.clicked.connect(self.importFiles)

    # ======================================================
    # 文件导入
    # ======================================================
    def importFiles(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频/音频",
            "",
            "视频 (*.mp4 *.flv *.mkv);;音频 (*.wav *.aac *.mp3);;所有文件 (*.*)"
        )

        if not paths:
            return

        for p in paths:
            info = self.fileManager.add_file(p)
            # 使用ffmpeg获取文件详细信息
            media_info = FFmpegService.get_file_info(p)
            if media_info:
                info.duration = media_info.get('duration')
                info.size = media_info.get('size')
                info.audio_format = media_info.get('audio_format')
                info.video_format = media_info.get('video_format')
                info.bit_rate = media_info.get('bit_rate')
                info.sample_rate = media_info.get('sample_rate')
                info.channels = media_info.get('channels')
                info.resolution = media_info.get('resolution')
                info.fps = media_info.get('fps')
            
            self.addFileToTable(info)

    # ======================================================
    # 渲染表格行
    # ======================================================
    def addFileToTable(self, info: FileInfo):
        row = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row)

        # 复选框
        col = self.COLS["check"]["index"]
        checkbox = QCheckBox()
        checkbox.setChecked(info.selected)

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(self.COLS["check"]["align"])
        self.tableWidget.setCellWidget(row, col, widget)

        # 文件名
        self._set_cell(row, "name", info.filename)

        # 时长
        text = f"{info.duration:.2f}s" if info.duration else "-"
        self._set_cell(row, "duration", text)

        # 大小
        text = f"{info.size/1024/1024:.2f} MB" if info.size else "-"
        self._set_cell(row, "size", text)

        # 分辨率
        text = info.resolution if info.resolution else "-"
        self._set_cell(row, "resolution", text)

        # 帧率
        text = f"{info.fps} fps" if info.fps else "-"
        self._set_cell(row, "fps", text)

        # 视频格式
        text = info.video_format if info.video_format else "-"
        self._set_cell(row, "vformat", text)

        # 音频格式
        text = info.audio_format if info.audio_format else "-"
        self._set_cell(row, "aformat", text)

        # 路径
        self._set_cell(row, "path", info.filepath)

    # ======================================================
    # 通用设置单元格方法
    # ======================================================
    def _set_cell(self, row: int, col_name: str, text: str):
        col_def = self.COLS[col_name]
        index = col_def["index"]
        align = col_def["align"]

        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        self.tableWidget.setItem(row, index, item)

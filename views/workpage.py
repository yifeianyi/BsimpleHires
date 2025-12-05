from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QFileDialog, QTableWidgetItem,
    QCheckBox, QHBoxLayout, QWidget
)
from PyQt6.QtCore import Qt

from models import FileInfo, FileManager


class WorkPage(QWidget):

    # ======================================================
    # 列定义（结构化方案）
    # ======================================================
    COLS = {
        "check":   {"index": 0, "title": "全选",      "align": Qt.AlignmentFlag.AlignCenter},
        "name":    {"index": 1, "title": "文件名",    "align": Qt.AlignmentFlag.AlignLeft},
        "duration": {"index": 2, "title": "时长",     "align": Qt.AlignmentFlag.AlignCenter},
        "size":    {"index": 3, "title": "大小",      "align": Qt.AlignmentFlag.AlignRight},
        "format":  {"index": 4, "title": "音频格式",  "align": Qt.AlignmentFlag.AlignCenter},
        "path":    {"index": 5, "title": "位置",      "align": Qt.AlignmentFlag.AlignLeft},
    }

    def __init__(self):
        super().__init__()
        uic.loadUi("ui/workPage.ui", self)

        # 后端数据管理器
        self.fileManager = FileManager()

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

        # 音频格式
        text = info.audio_format if info.audio_format else "-"
        self._set_cell(row, "format", text)

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

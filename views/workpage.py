import os

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QWidget,
)

from models import FileInfo, FileManager
from services.converter_service import ConversionProgress
from services.ffmpeg_service import FFmpegService
from services.settings_service import SettingsService
from utils.logging_utils import get_logger
from utils.path_utils import get_resource_path
from views.progress_dialog import ProgressDialog
from views.settings_dialog import SettingsDialog
from workers.conversion_worker import ConversionThreadManager

logger = get_logger(__name__)


class WorkPage(QWidget):
    COLS = {
        "check": {"index": 0, "title": "全选", "align": Qt.AlignmentFlag.AlignCenter},
        "name": {"index": 1, "title": "文件名", "align": Qt.AlignmentFlag.AlignLeft},
        "duration": {"index": 2, "title": "时长", "align": Qt.AlignmentFlag.AlignCenter},
        "size": {"index": 3, "title": "大小", "align": Qt.AlignmentFlag.AlignRight},
        "resolution": {"index": 4, "title": "分辨率", "align": Qt.AlignmentFlag.AlignCenter},
        "fps": {"index": 5, "title": "帧率", "align": Qt.AlignmentFlag.AlignCenter},
        "vformat": {"index": 6, "title": "视频格式", "align": Qt.AlignmentFlag.AlignCenter},
        "aformat": {"index": 7, "title": "音频格式", "align": Qt.AlignmentFlag.AlignCenter},
        "sample_rate": {"index": 8, "title": "采样率", "align": Qt.AlignmentFlag.AlignCenter},
        "bit_rate": {"index": 9, "title": "音频码率", "align": Qt.AlignmentFlag.AlignCenter},
    }

    def __init__(self):
        super().__init__()
        uic.loadUi(get_resource_path("ui/workPage.ui"), self)

        self.fileManager = FileManager()
        self.settings = SettingsService.load()
        self.last_output_dir = ""

        self.conversion_manager = ConversionThreadManager()
        self.progress_dialog = None
        self.cancel_requested = False

        if not FFmpegService.check_ffmpeg_available():
            logger.warning(FFmpegService.get_availability_error())

        self.ImportButton.clicked.connect(self.importFiles)
        self.WorkButton.clicked.connect(self.startConversion)
        self._init_table_behavior()
        self._init_runtime_buttons()

    def _init_table_behavior(self):
        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tableWidget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.deleteShortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.tableWidget)
        self.deleteShortcut.activated.connect(self.removeSelectedRows)

    def _init_runtime_buttons(self):
        self.RemoveButton = QPushButton("移除选中", self)
        self.ClearButton = QPushButton("清空列表", self)
        self.SettingsButton = QPushButton("设置", self)
        self.horizontalLayout.insertWidget(1, self.RemoveButton)
        self.horizontalLayout.insertWidget(2, self.ClearButton)
        self.horizontalLayout.addWidget(self.SettingsButton)
        self.RemoveButton.clicked.connect(self.removeSelectedRows)
        self.ClearButton.clicked.connect(self.clearFiles)
        self.SettingsButton.clicked.connect(self.openSettingsDialog)

    def importFiles(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频/音频",
            "",
            "视频 (*.mp4 *.flv *.mkv);;音频 (*.wav *.aac *.mp3);;所有文件 (*.*)",
        )

        if not paths:
            return

        duplicate_count = 0
        for path in paths:
            if self.fileManager.find_by_path(path):
                duplicate_count += 1
                continue

            info = self.fileManager.add_file(path)
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

            self.addFileToTable(info)

        if duplicate_count:
            QMessageBox.information(
                self,
                "已跳过重复文件",
                f"有 {duplicate_count} 个已在列表中的文件被跳过。",
            )

    def addFileToTable(self, info: FileInfo):
        row = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row)

        checkbox = QCheckBox()
        checkbox.setChecked(info.selected)
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(self.COLS["check"]["align"])
        self.tableWidget.setCellWidget(row, self.COLS["check"]["index"], widget)

        self._set_cell(row, "name", info.filename)
        name_item = self.tableWidget.item(row, self.COLS["name"]["index"])
        if name_item:
            name_item.setToolTip(info.filepath)

        self._set_cell(row, "duration", f"{info.duration:.2f}s" if info.duration else "-")
        self._set_cell(row, "size", f"{info.size / 1024 / 1024:.2f} MB" if info.size else "-")
        self._set_cell(row, "resolution", info.resolution or "-")
        self._set_cell(row, "fps", f"{info.fps} fps" if info.fps else "-")
        self._set_cell(row, "vformat", info.video_format or "-")
        self._set_cell(row, "aformat", info.audio_format or "-")
        self._set_cell(row, "sample_rate", f"{info.sample_rate} Hz" if info.sample_rate else "-")
        self._set_cell(row, "bit_rate", f"{info.bit_rate / 1000:.0f} kbps" if info.bit_rate else "-")

    def startConversion(self):
        logger.info("用户点击格式转换按钮")

        if self.conversion_manager.is_running():
            logger.warning("已有转换任务在进行中")
            QMessageBox.warning(self, "警告", "已有转换任务正在进行中，请等待完成")
            return

        selected_files = self.get_selected_files()
        logger.info("获取到 %s 个选中文件", len(selected_files))

        if not selected_files:
            logger.warning("没有选中任何文件")
            QMessageBox.warning(self, "警告", "请先选择要转换的文件")
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            self.last_output_dir or self.settings.default_output_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if not output_dir:
            logger.info("用户取消了输出目录选择")
            return

        self.last_output_dir = output_dir
        naming_text = "自动递增避免覆盖" if self.settings.naming_strategy == "auto_increment" else "直接覆盖同名输出"
        reply = QMessageBox.question(
            self,
            "确认转换",
            (
                f"即将转换 {len(selected_files)} 个文件到:\n{output_dir}\n\n"
                "输出文件名: 原文件名_bsimple.mov\n"
                f"命名策略: {naming_text}\n"
                f"并发数: {self.settings.max_workers}\n"
                "输出格式: MOV 容器(保留视频 + PCM 24bit 音频)\n\n"
                "是否继续？"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            logger.info("用户取消了转换操作")
            return

        self.cancel_requested = False
        self.show_progress_dialog(len(selected_files))

        success = self.conversion_manager.start_conversion(
            selected_files,
            output_dir,
            progress_callback=self.on_conversion_progress,
            finished_callback=self.on_conversion_finished,
            error_callback=self.on_conversion_error,
            max_workers=self.settings.max_workers,
        )
        if not success:
            logger.error("无法启动转换任务")
            if self.progress_dialog:
                self.progress_dialog.close()
            QMessageBox.critical(self, "错误", "无法启动转换任务")

    def get_selected_files(self) -> list[str]:
        selected_files: list[str] = []
        for row in range(self.tableWidget.rowCount()):
            widget = self.tableWidget.cellWidget(row, self.COLS["check"]["index"])
            if not widget:
                continue

            checkbox = widget.findChild(QCheckBox)
            if checkbox and checkbox.isChecked() and row < len(self.fileManager.files):
                selected_files.append(self.fileManager.files[row].filepath)
        return selected_files

    def removeSelectedRows(self):
        selected_rows = sorted({index.row() for index in self.tableWidget.selectionModel().selectedRows()})
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在列表中选择要移除的文件。")
            return

        self.fileManager.remove_by_indices(selected_rows)
        for row in reversed(selected_rows):
            self.tableWidget.removeRow(row)

    def clearFiles(self):
        if self.tableWidget.rowCount() == 0:
            return

        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空当前文件列表吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.fileManager.clear()
        self.tableWidget.setRowCount(0)

    def show_progress_dialog(self, total_files: int):
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.cancel_requested.connect(self.on_cancel_conversion)
        self.progress_dialog.setWindowTitle(f"转换进度 - {total_files} 个文件")
        self.progress_dialog.show()
        logger.info("进度对话框已显示，共 %s 个文件", total_files)

    def on_cancel_conversion(self):
        logger.info("用户请求取消转换")
        reply = QMessageBox.question(
            self,
            "确认取消",
            "确定要取消当前转换任务吗？\n已转换的文件将保留。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.cancel_requested = True
        self.conversion_manager.stop_conversion()
        if self.progress_dialog:
            self.progress_dialog.set_cancelling()

    def on_conversion_progress(self, progress_info: ConversionProgress):
        if self.progress_dialog:
            self.progress_dialog.update_progress(progress_info)

    def on_conversion_finished(self, results: list[bool]):
        logger.info("转换完成回调，结果: %s", results)
        success_count = sum(results)
        total_count = len(results)

        if self.progress_dialog:
            if self.cancel_requested:
                self.progress_dialog.set_conversion_cancelled(success_count, total_count)
            else:
                self.progress_dialog.set_conversion_complete(success_count, total_count)

        if self.cancel_requested:
            QMessageBox.information(
                self,
                "已取消",
                f"转换已取消：已完成 {success_count} 个，未完成 {total_count - success_count} 个",
            )
            self.cancel_requested = False
            return

        if success_count == total_count:
            self._maybe_open_output_dir()
            QMessageBox.information(self, "转换完成", f"所有 {total_count} 个文件转换成功！")
            return

        if success_count > 0:
            self._maybe_open_output_dir()

        detail = self.progress_dialog.statusLabel.text().replace("状态: ", "") if self.progress_dialog else ""
        QMessageBox.warning(
            self,
            "转换完成",
            f"转换完成：成功 {success_count} 个，失败 {total_count - success_count} 个。\n\n{detail}",
        )

    def on_conversion_error(self, error_msg: str):
        logger.error("转换错误回调: %s", error_msg)
        if self.progress_dialog:
            self.progress_dialog.set_conversion_error(error_msg)
        QMessageBox.critical(self, "转换错误", error_msg)

    def openSettingsDialog(self):
        dialog = SettingsDialog(self.settings, self)
        if not dialog.exec():
            return

        self.settings = dialog.get_settings()
        SettingsService.save(self.settings)
        SettingsService.invalidate_cache()
        self.settings = SettingsService.load()
        QMessageBox.information(self, "设置已保存", "设置已生效。")

    def _maybe_open_output_dir(self):
        if not self.settings.open_output_dir_after_completion:
            return
        if not self.last_output_dir or not os.path.isdir(self.last_output_dir):
            return

        try:
            os.startfile(self.last_output_dir)
        except OSError as exc:
            logger.warning("打开输出目录失败: %s - %s", self.last_output_dir, exc)

    def _set_cell(self, row: int, col_name: str, text: str):
        col_def = self.COLS[col_name]
        item = QTableWidgetItem(text)
        item.setTextAlignment(col_def["align"])
        self.tableWidget.setItem(row, col_def["index"], item)

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QFileDialog, QTableWidgetItem,
    QCheckBox, QHBoxLayout, QWidget, QMessageBox, QPushButton,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShortcut, QKeySequence

from models import FileInfo, FileManager
from services.ffmpeg_service import FFmpegService
from services.converter_service import ConversionProgress
from utils.path_utils import get_resource_path
from workers.conversion_worker import ConversionThreadManager
from views.progress_dialog import ProgressDialog


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
        "sample_rate": {"index": 8, "title": "采样率",   "align": Qt.AlignmentFlag.AlignCenter},
        "bit_rate":  {"index": 9, "title": "音频码率",  "align": Qt.AlignmentFlag.AlignCenter},
    }

    def __init__(self):
        super().__init__()
        uic.loadUi(get_resource_path("ui/workPage.ui"), self)

        # 后端数据管理器
        self.fileManager = FileManager()

        # 转换线程管理器
        self.conversion_manager = ConversionThreadManager()
        
        # 进度对话框
        self.progress_dialog = None
        self.cancel_requested = False

        # 检查ffmpeg是否可用
        if not FFmpegService.check_ffmpeg_available():
            print(f"警告: {FFmpegService.get_availability_error()}")

        # UI 按钮
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
        self.horizontalLayout.insertWidget(1, self.RemoveButton)
        self.horizontalLayout.insertWidget(2, self.ClearButton)
        self.RemoveButton.clicked.connect(self.removeSelectedRows)
        self.ClearButton.clicked.connect(self.clearFiles)

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

        duplicate_count = 0
        for p in paths:
            if self.fileManager.find_by_path(p):
                duplicate_count += 1
                continue

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

        if duplicate_count:
            QMessageBox.information(
                self,
                "已跳过重复文件",
                f"有 {duplicate_count} 个已在列表中的文件被跳过。"
            )

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
        name_item = self.tableWidget.item(row, self.COLS["name"]["index"])
        if name_item:
            name_item.setToolTip(info.filepath)

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

        # 采样率
        text = f"{info.sample_rate} Hz" if info.sample_rate else "-"
        self._set_cell(row, "sample_rate", text)

        # 码率
        text = f"{info.bit_rate/1000:.0f} kbps" if info.bit_rate else "-"
        self._set_cell(row, "bit_rate", text)

    # ======================================================
    # 格式转换功能
    # ======================================================
    def startConversion(self):
        """开始格式转换"""
        print(f"[WorkPage] 用户点击格式转换按钮")
        
        # 检查是否有正在进行的转换
        if self.conversion_manager.is_running():
            print(f"[WorkPage] 警告: 已有转换任务在进行中")
            QMessageBox.warning(self, "警告", "已有转换任务正在进行中，请等待完成")
            return
        
        # 获取选中的文件
        selected_files = self.get_selected_files()
        print(f"[WorkPage] 获取到 {len(selected_files)} 个选中文件")
        
        if not selected_files:
            print(f"[WorkPage] 警告: 没有选中任何文件")
            QMessageBox.warning(self, "警告", "请先选择要转换的文件")
            return
        
        # 打印选中的文件列表
        # for i, file in enumerate(selected_files):
        #     print(f"[WorkPage] 选中文件 {i+1}: {file}")
        
        # 选择输出目录
        print(f"[WorkPage] 请求用户选择输出目录")
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not output_dir:
            print(f"[WorkPage] 用户取消了输出目录选择")
            return
        
        print(f"[WorkPage] 用户选择输出目录: {output_dir}")
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认转换",
            f"即将转换 {len(selected_files)} 个文件到:\n{output_dir}\n\n"
            "输出文件名: 原文件名_bsimple.mov（如重名则自动递增）\n"
            "输出格式: MOV容器(保留视频+PCM 24bit音频)\n\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            print(f"[WorkPage] 用户取消了转换操作")
            return
        
        print(f"[WorkPage] 用户确认开始转换")
        self.cancel_requested = False
        
        # 创建并显示进度对话框
        print(f"[WorkPage] 创建进度对话框")
        self.show_progress_dialog(len(selected_files))
        
        # 启动转换
        print(f"[WorkPage] 启动多线程转换管理器")
        # 根据文件数量动态设置并发数，最多4个线程
        max_workers = min(4, max(2, len(selected_files) // 2))
        print(f"[WorkPage] 使用并发线程数: {max_workers}")
        
        success = self.conversion_manager.start_conversion(
            selected_files,
            output_dir,
            progress_callback=self.on_conversion_progress,
            finished_callback=self.on_conversion_finished,
            error_callback=self.on_conversion_error,
            max_workers=max_workers
        )
        
        if not success:
            print(f"[WorkPage] 错误: 无法启动转换任务")
            self.progress_dialog.close()
            QMessageBox.critical(self, "错误", "无法启动转换任务")
        # else:
        #     print(f"[WorkPage] 转换任务已成功启动")
    
    def get_selected_files(self) -> list[str]:
        """获取选中的文件列表"""
        selected_files = []
        for row in range(self.tableWidget.rowCount()):
            # 获取复选框状态
            widget = self.tableWidget.cellWidget(row, self.COLS["check"]["index"])
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # 从FileInfo对象获取文件路径
                    if row < len(self.fileManager.files):
                        selected_files.append(self.fileManager.files[row].filepath)
        return selected_files

    def removeSelectedRows(self):
        """移除表格中选中的行。"""
        selected_rows = sorted({index.row() for index in self.tableWidget.selectionModel().selectedRows()})
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在列表中选择要移除的文件。")
            return

        self.fileManager.remove_by_indices(selected_rows)
        for row in reversed(selected_rows):
            self.tableWidget.removeRow(row)

    def clearFiles(self):
        """清空文件列表。"""
        if self.tableWidget.rowCount() == 0:
            return

        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空当前文件列表吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.fileManager.clear()
        self.tableWidget.setRowCount(0)
    
    def show_progress_dialog(self, total_files: int):
        """显示进度对话框"""
        self.progress_dialog = ProgressDialog(self)
        
        # 连接取消信号
        self.progress_dialog.cancel_requested.connect(self.on_cancel_conversion)
        
        # 设置窗口标题显示任务数量
        self.progress_dialog.setWindowTitle(f"转换进度 - {total_files} 个文件")
        
        # 使用show()而不是exec()来避免阻塞
        self.progress_dialog.show()
        print(f"[WorkPage] 进度对话框已显示，共 {total_files} 个文件")
    
    def on_cancel_conversion(self):
        """处理用户取消转换请求"""
        print(f"[WorkPage] 用户请求取消转换")
        
        reply = QMessageBox.question(
            self,
            "确认取消",
            "确定要取消当前转换任务吗？\n已转换的文件将保留。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            print(f"[WorkPage] 用户确认取消转换")
            self.cancel_requested = True
            # 停止转换
            self.conversion_manager.stop_conversion()
            
            # 更新进度对话框状态
            if self.progress_dialog:
                self.progress_dialog.set_cancelling()
        # else:
        #     print(f"[WorkPage] 用户取消取消操作")
    
    def on_conversion_progress(self, progress_info: ConversionProgress):
        """转换进度更新"""
        print(f"[WorkPage] 进度更新: {progress_info.current_file} - {progress_info.current_progress:.1f}% - {progress_info.status}")
        
        # 更新进度对话框
        if self.progress_dialog:
            self.progress_dialog.update_progress(progress_info)
    
    def on_conversion_finished(self, results: list[bool]):
        """转换完成"""
        print(f"[WorkPage] 转换完成回调，结果: {results}")
        
        # 统计结果
        success_count = sum(results)
        total_count = len(results)
        
        print(f"[WorkPage] 转换统计: 成功 {success_count}/{total_count}")
        
        # 更新进度对话框
        if self.progress_dialog:
            if self.cancel_requested:
                self.progress_dialog.set_conversion_cancelled(success_count, total_count)
            else:
                self.progress_dialog.set_conversion_complete(success_count, total_count)
        
        # 显示结果消息
        if self.cancel_requested:
            QMessageBox.information(
                self,
                "已取消",
                f"转换已取消：已完成 {success_count} 个，未完成 {total_count - success_count} 个"
            )
            self.cancel_requested = False
            return

        if success_count == total_count:
            print(f"[WorkPage] 所有文件转换成功")
            QMessageBox.information(
                self,
                "转换完成",
                f"所有 {total_count} 个文件转换成功！"
            )
        else:
            print(f"[WorkPage] 部分文件转换失败")
            QMessageBox.warning(
                self,
                "转换完成",
                f"转换完成：成功 {success_count} 个，失败 {total_count - success_count} 个。\n\n"
                f"{self.progress_dialog.statusLabel.text().replace('状态: ', '') if self.progress_dialog else ''}"
            )
    
    def on_conversion_error(self, error_msg: str):
        """转换错误"""
        print(f"[WorkPage] 转换错误回调: {error_msg}")
        
        # 更新进度对话框
        if self.progress_dialog:
            self.progress_dialog.set_conversion_error(error_msg)
        
        # 显示错误消息
        QMessageBox.critical(self, "转换错误", error_msg)
    
    # def showSettings(self):
    #     """显示设置对话框"""
    #     QMessageBox.information(self, "设置", "设置功能暂未实现")

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


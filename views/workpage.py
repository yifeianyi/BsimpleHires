from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QFileDialog, QTableWidgetItem,
    QCheckBox, QHBoxLayout, QWidget, QMessageBox,
    QProgressBar, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, QThread

from models import FileInfo, FileManager
from services.ffmpeg_service import FFmpegService
from services.converter_service import ConversionProgress
from workers.conversion_worker import ConversionThreadManager


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

        # 转换线程管理器
        self.conversion_manager = ConversionThreadManager()

        # 检查ffmpeg是否可用
        if not FFmpegService.check_ffmpeg_available():
            print("警告: 未检测到ffmpeg/ffprobe，无法读取媒体文件信息")

        # UI 按钮
        self.ImportButton.clicked.connect(self.importFiles)
        self.WorkButton.clicked.connect(self.startConversion)
        self.SettingButton.clicked.connect(self.showSettings)

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
        for i, file in enumerate(selected_files):
            print(f"[WorkPage] 选中文件 {i+1}: {file}")
        
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
            "输出格式: MOV容器(保留视频+PCM 24bit音频)\n\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            print(f"[WorkPage] 用户取消了转换操作")
            return
        
        print(f"[WorkPage] 用户确认开始转换")
        
        # 创建进度对话框
        print(f"[WorkPage] 创建进度对话框")
        self.create_progress_dialog()
        
        # 启动转换
        print(f"[WorkPage] 启动转换管理器")
        success = self.conversion_manager.start_conversion(
            selected_files,
            output_dir,
            progress_callback=self.on_conversion_progress,
            finished_callback=self.on_conversion_finished,
            error_callback=self.on_conversion_error
        )
        
        if not success:
            print(f"[WorkPage] 错误: 无法启动转换任务")
            QMessageBox.critical(self, "错误", "无法启动转换任务")
        else:
            print(f"[WorkPage] 转换任务已成功启动")
    
    def get_selected_files(self) -> list[str]:
        """获取选中的文件列表"""
        selected_files = []
        for row in range(self.tableWidget.rowCount()):
            # 获取复选框状态
            widget = self.tableWidget.cellWidget(row, self.COLS["check"]["index"])
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # 获取文件路径
                    path_item = self.tableWidget.item(row, self.COLS["path"]["index"])
                    if path_item:
                        selected_files.append(path_item.text())
        return selected_files
    
    def create_progress_dialog(self):
        """创建进度显示对话框"""
        self.progress_dialog = QWidget(self)
        self.progress_dialog.setWindowTitle("转换进度")
        self.progress_dialog.setFixedSize(400, 150)
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        layout = QVBoxLayout()
        
        # 当前文件标签
        self.current_file_label = QLabel("准备开始...")
        layout.addWidget(self.current_file_label)
        
        # 总体进度
        self.total_progress_label = QLabel("总体进度: 0/0")
        layout.addWidget(self.total_progress_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("状态: 等待中")
        layout.addWidget(self.status_label)
        
        self.progress_dialog.setLayout(layout)
        self.progress_dialog.show()
    
    def on_conversion_progress(self, progress_info: ConversionProgress):
        """转换进度更新"""
        print(f"[WorkPage] 进度更新: {progress_info.current_file} - {progress_info.current_progress:.1f}% - {progress_info.status}")
        
        # 更新当前文件
        self.current_file_label.setText(f"当前文件: {progress_info.current_file}")
        
        # 更新总体进度
        self.total_progress_label.setText(
            f"总体进度: {progress_info.completed_files}/{progress_info.total_files}"
        )
        
        # 更新进度条
        total_progress = (progress_info.completed_files / progress_info.total_files) * 100
        total_progress += (progress_info.current_progress / progress_info.total_files)
        self.progress_bar.setValue(int(total_progress))
        
        # 更新状态
        self.status_label.setText(f"状态: {progress_info.status}")
        
        # 如果有错误，显示错误信息
        if progress_info.error_message:
            print(f"[WorkPage] 错误信息: {progress_info.error_message}")
            self.status_label.setText(f"状态: {progress_info.error_message}")
    
    def on_conversion_finished(self, results: list[bool]):
        """转换完成"""
        print(f"[WorkPage] 转换完成回调，结果: {results}")
        self.progress_dialog.close()
        
        # 统计结果
        success_count = sum(results)
        total_count = len(results)
        
        print(f"[WorkPage] 转换统计: 成功 {success_count}/{total_count}")
        
        # 显示结果
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
                f"转换完成：成功 {success_count} 个，失败 {total_count - success_count} 个"
            )
    
    def on_conversion_error(self, error_msg: str):
        """转换错误"""
        print(f"[WorkPage] 转换错误回调: {error_msg}")
        self.progress_dialog.close()
        QMessageBox.critical(self, "转换错误", error_msg)
    
    def showSettings(self):
        """显示设置对话框"""
        QMessageBox.information(self, "设置", "设置功能暂未实现")

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


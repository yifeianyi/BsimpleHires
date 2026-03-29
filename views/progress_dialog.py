from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QScrollArea, QVBoxLayout, QWidget
from PyQt6.QtCore import pyqtSignal
from services.converter_service import ConversionProgress
from utils.path_utils import get_resource_path


class ProgressDialog(QDialog):
    """转换进度对话框"""
    
    # 定义信号
    cancel_requested = pyqtSignal()  # 用户请求取消
    
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/ProgressBar.ui"), self)
        self.file_progress_widgets: dict[str, tuple[QLabel, QProgressBar]] = {}
        self._init_active_progress_area()
        
        # 不设置窗口模态，允许后台转换继续进行
        # self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # 连接取消按钮信号
        self.cancelButton.clicked.connect(self.on_cancel_clicked)
        
        # 初始化状态
        self.reset_progress()

    def _init_active_progress_area(self):
        """Create a scrollable area for per-file progress bars."""
        self.activeProgressArea = QScrollArea(self)
        self.activeProgressArea.setWidgetResizable(True)
        self.activeProgressArea.setMinimumHeight(120)

        self.activeProgressContent = QWidget()
        self.activeProgressLayout = QVBoxLayout(self.activeProgressContent)
        self.activeProgressLayout.setContentsMargins(0, 0, 0, 0)
        self.activeProgressLayout.setSpacing(8)
        self.activeProgressArea.setWidget(self.activeProgressContent)

        self.activeProgressTitleLabel = QLabel("正在转换的文件", self)
        title_index = self.verticalLayout.indexOf(self.statusLabel)
        self.verticalLayout.insertWidget(title_index, self.activeProgressTitleLabel)
        self.verticalLayout.insertWidget(title_index + 1, self.activeProgressArea)

    def reset_progress(self):
        """重置进度显示"""
        self.currentFileLabel.setText("当前文件: 准备中...")
        self.totalProgressLabel.setText("总体进度: 0/0")
        self.progressBar.setValue(0)
        self.statusLabel.setText("状态: 等待中")
        self._render_active_file_progresses([])

    def _create_file_progress_widget(self, filename: str) -> tuple[QLabel, QProgressBar]:
        label = QLabel(filename, self.activeProgressContent)
        progress_bar = QProgressBar(self.activeProgressContent)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        self.activeProgressLayout.addWidget(label)
        self.activeProgressLayout.addWidget(progress_bar)
        return label, progress_bar

    def _render_active_file_progresses(self, active_progresses: list[tuple[str, float]]):
        active_names = {name for name, _ in active_progresses}

        for filename in list(self.file_progress_widgets.keys()):
            if filename in active_names:
                continue

            label, progress_bar = self.file_progress_widgets.pop(filename)
            self.activeProgressLayout.removeWidget(label)
            self.activeProgressLayout.removeWidget(progress_bar)
            label.deleteLater()
            progress_bar.deleteLater()

        for filename, progress in active_progresses:
            if filename not in self.file_progress_widgets:
                self.file_progress_widgets[filename] = self._create_file_progress_widget(filename)

            label, progress_bar = self.file_progress_widgets[filename]
            label.setText(filename)
            progress_bar.setValue(int(progress))

        self.activeProgressArea.setVisible(bool(active_progresses))
        self.activeProgressTitleLabel.setVisible(bool(active_progresses))
    
    def update_progress(self, progress_info: ConversionProgress):
        """更新进度信息"""
        # 更新当前文件
        current_file = progress_info.current_file or "准备中..."
        self.currentFileLabel.setText(f"当前文件: {current_file}")
        
        # 更新总体进度
        active_threads_text = f" ({progress_info.active_threads} 线程)" if hasattr(progress_info, 'active_threads') and progress_info.active_threads > 0 else ""
        self.totalProgressLabel.setText(
            f"总体进度: {progress_info.completed_files}/{progress_info.total_files}{active_threads_text}"
        )
        
        # 直接使用汇总后的总体进度
        self.progressBar.setValue(int(progress_info.total_progress))
        self._render_active_file_progresses(progress_info.active_file_progresses)
        
        # 更新状态
        status_text = f"状态: {progress_info.status}"
        if progress_info.error_message:
            status_text += f" - {progress_info.error_message}"
        self.statusLabel.setText(status_text)
    
    def set_conversion_complete(self, success_count: int, total_count: int):
        """设置转换完成状态"""
        self.progressBar.setValue(100)
        self._render_active_file_progresses([])
        self.statusLabel.setText(f"状态: 转换完成 (成功: {success_count}/{total_count})")
        self.cancelButton.setText("关闭")
        self.enable_close()
    
    def set_conversion_error(self, error_msg: str):
        """设置转换错误状态"""
        self._render_active_file_progresses([])
        self.statusLabel.setText(f"状态: 转换失败 - {error_msg}")
        self.cancelButton.setText("关闭")
        self.enable_close()

    def set_cancelling(self):
        """设置正在取消状态。"""
        self.statusLabel.setText("状态: 正在取消...")
        self.cancelButton.setEnabled(False)

    def set_conversion_cancelled(self, success_count: int, total_count: int):
        """设置转换已取消状态。"""
        self._render_active_file_progresses([])
        self.statusLabel.setText(f"状态: 已取消 (已完成: {success_count}/{total_count})")
        self.cancelButton.setEnabled(True)
        self.cancelButton.setText("关闭")
        self.enable_close()
    
    def on_cancel_clicked(self):
        """取消按钮点击处理"""
        if self.cancelButton.text() == "取消":
            # 转换进行中，发出取消信号
            self.cancel_requested.emit()
        else:
            # 转换已完成或出错，关闭窗口
            self.close()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 如果转换正在进行，发出取消信号
        if self.cancelButton.text() == "取消":
            self.cancel_requested.emit()
            event.ignore()  # 不立即关闭，等待转换取消
        else:
            event.accept()  # 允许关闭
    
    def enable_close(self):
        """启用窗口关闭"""
        self.cancelButton.setEnabled(True)
        self.cancelButton.setText("关闭")
        # 窗口已经是非模态的，无需修改

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QVBoxLayout, QWidget

from services.converter_service import ConversionProgress
from utils.path_utils import get_resource_path


class ProgressDialog(QDialog):
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/ProgressBar.ui"), self)
        self.file_progress_widgets: dict[str, tuple[QWidget, QLabel, QLabel, QProgressBar]] = {}
        self._init_active_progress_area()
        self.cancelButton.clicked.connect(self.on_cancel_clicked)
        self.reset_progress()

    def _init_active_progress_area(self):
        self.activeProgressArea = QScrollArea(self)
        self.activeProgressArea.setWidgetResizable(True)
        self.activeProgressArea.setMinimumHeight(120)
        self.activeProgressArea.setMaximumHeight(220)
        self.activeProgressArea.setFrameShape(QScrollArea.Shape.NoFrame)

        self.activeProgressContent = QWidget()
        self.activeProgressLayout = QVBoxLayout(self.activeProgressContent)
        self.activeProgressLayout.setContentsMargins(0, 0, 0, 0)
        self.activeProgressLayout.setSpacing(8)
        self.activeProgressArea.setWidget(self.activeProgressContent)

        self.activeProgressTitleLabel = QLabel("正在转换的文件", self)
        title_index = self.verticalLayout.indexOf(self.statusLabel)
        self.verticalLayout.insertWidget(title_index, self.activeProgressTitleLabel)
        self.verticalLayout.insertWidget(title_index + 1, self.activeProgressArea)
        self.activeProgressArea.setVisible(False)
        self.activeProgressTitleLabel.setVisible(False)

    def reset_progress(self):
        self.currentFileLabel.setText("当前文件: 准备中...")
        self.totalProgressLabel.setText("总体进度: 0/0")
        self.progressBar.setValue(0)
        self.statusLabel.setText("状态: 等待中")
        self._render_active_file_progresses([])

    def _create_file_progress_widget(self, task_id: str) -> tuple[QWidget, QLabel, QLabel, QProgressBar]:
        container = QWidget(self.activeProgressContent)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        label = QLabel(filename, container)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        percent_label = QLabel("0%", container)
        percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        percent_label.setMinimumWidth(42)

        progress_bar = QProgressBar(container)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(False)

        header_layout.addWidget(label, 1)
        header_layout.addWidget(percent_label)
        container_layout.addLayout(header_layout)
        container_layout.addWidget(progress_bar)
        self.activeProgressLayout.addWidget(container)
        container.setProperty("task_id", task_id)
        return container, label, percent_label, progress_bar

    def _set_label_text(self, label: QLabel, text: str):
        label.setProperty("display_text", text)
        metrics = QFontMetrics(label.font())
        available_width = max(label.width(), 220)
        label.setText(metrics.elidedText(text, Qt.TextElideMode.ElideMiddle, available_width))

    def _render_active_file_progresses(self, active_progresses: list[tuple[str, str, float]]):
        active_ids = {task_id for task_id, _, _ in active_progresses}
        for task_id in list(self.file_progress_widgets.keys()):
            if task_id in active_ids:
                continue
            container, _, _, _ = self.file_progress_widgets.pop(task_id)
            self.activeProgressLayout.removeWidget(container)
            container.deleteLater()

        for task_id, display_name, progress in active_progresses:
            if task_id not in self.file_progress_widgets:
                self.file_progress_widgets[task_id] = self._create_file_progress_widget(task_id)

            _, label, percent_label, progress_bar = self.file_progress_widgets[task_id]
            label.setToolTip(task_id)
            self._set_label_text(label, display_name)
            percent_label.setText(f"{int(progress)}%")
            progress_bar.setValue(int(progress))

        visible = bool(active_progresses)
        self.activeProgressArea.setVisible(visible)
        self.activeProgressTitleLabel.setVisible(visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for _, label, _, _ in self.file_progress_widgets.values():
            self._set_label_text(label, label.property("display_text") or label.toolTip())

    def update_progress(self, progress_info: ConversionProgress):
        current_file = progress_info.current_file or "准备中..."
        self.currentFileLabel.setText(f"当前文件: {current_file}")

        active_threads_text = f" ({progress_info.active_threads} 线程)" if progress_info.active_threads > 0 else ""
        self.totalProgressLabel.setText(
            f"总体进度: {progress_info.completed_files}/{progress_info.total_files}{active_threads_text}"
        )
        self.progressBar.setValue(int(progress_info.total_progress))
        self._render_active_file_progresses(progress_info.active_file_progresses)

        status_text = f"状态: {progress_info.status}"
        if progress_info.error_message:
            status_text += f" - {progress_info.error_message}"
        self.statusLabel.setText(status_text)

    def set_conversion_complete(self, success_count: int, total_count: int):
        self.progressBar.setValue(100)
        self._render_active_file_progresses([])
        self.statusLabel.setText(f"状态: 转换完成 (成功: {success_count}/{total_count})")
        self.cancelButton.setText("关闭")
        self.enable_close()

    def set_conversion_error(self, error_msg: str):
        self._render_active_file_progresses([])
        self.statusLabel.setText(f"状态: 转换失败 - {error_msg}")
        self.cancelButton.setText("关闭")
        self.enable_close()

    def set_cancelling(self):
        self.statusLabel.setText("状态: 正在取消...")
        self.cancelButton.setEnabled(False)

    def set_conversion_cancelled(self, success_count: int, total_count: int):
        self._render_active_file_progresses([])
        self.statusLabel.setText(f"状态: 已取消 (已完成 {success_count}/{total_count})")
        self.cancelButton.setEnabled(True)
        self.cancelButton.setText("关闭")
        self.enable_close()

    def on_cancel_clicked(self):
        if self.cancelButton.text() == "取消":
            self.cancel_requested.emit()
        else:
            self.close()

    def closeEvent(self, event):
        if self.cancelButton.text() == "取消":
            self.cancel_requested.emit()
            event.ignore()
        else:
            event.accept()

    def enable_close(self):
        self.cancelButton.setEnabled(True)
        self.cancelButton.setText("关闭")

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import Qt, pyqtSignal
from services.converter_service import ConversionProgress


class ProgressDialog(QDialog):
    """转换进度对话框"""
    
    # 定义信号
    cancel_requested = pyqtSignal()  # 用户请求取消
    
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("ui/ProgressBar.ui", self)
        
        # 不设置窗口模态，允许后台转换继续进行
        # self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # 连接取消按钮信号
        self.cancelButton.clicked.connect(self.on_cancel_clicked)
        
        # 初始化状态
        self.reset_progress()
    
    def reset_progress(self):
        """重置进度显示"""
        self.currentFileLabel.setText("当前文件: 准备中...")
        self.totalProgressLabel.setText("总体进度: 0/0")
        self.progressBar.setValue(0)
        self.statusLabel.setText("状态: 等待中")
    
    def update_progress(self, progress_info: ConversionProgress):
        """更新进度信息"""
        # 更新当前文件
        self.currentFileLabel.setText(f"当前文件: {progress_info.current_file}")
        
        # 更新总体进度
        self.totalProgressLabel.setText(
            f"总体进度: {progress_info.completed_files}/{progress_info.total_files}"
        )
        
        # 计算总体进度百分比
        if progress_info.total_files > 0:
            # 已完成文件的进度 + 当前文件的进度
            file_progress = (progress_info.completed_files / progress_info.total_files) * 100
            # 当前文件进度应该除以100再乘以单个文件占总进度的比例
            current_file_progress = (progress_info.current_progress / 100) * (100 / progress_info.total_files)
            total_progress = file_progress + current_file_progress
            self.progressBar.setValue(int(total_progress))
        
        # 更新状态
        status_text = f"状态: {progress_info.status}"
        if progress_info.error_message:
            status_text += f" - {progress_info.error_message}"
        self.statusLabel.setText(status_text)
    
    def set_conversion_complete(self, success_count: int, total_count: int):
        """设置转换完成状态"""
        self.progressBar.setValue(100)
        self.statusLabel.setText(f"状态: 转换完成 (成功: {success_count}/{total_count})")
        self.cancelButton.setText("关闭")
        self.enable_close()
    
    def set_conversion_error(self, error_msg: str):
        """设置转换错误状态"""
        self.statusLabel.setText(f"状态: 转换失败 - {error_msg}")
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
        self.cancelButton.setText("关闭")
        # 窗口已经是非模态的，无需修改
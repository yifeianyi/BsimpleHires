from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
import sys
import os
from views.mainwindow import MainWindow

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持开发环境和打包后的环境"""
    try:
        # PyInstaller 创建临时文件夹，将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except AttributeError:
        # 开发环境，使用当前工作目录
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_resource_path("assets/logo.ico")))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

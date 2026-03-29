from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
import sys
import os
from views.mainwindow import MainWindow

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持开发环境和打包后的环境"""
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller临时目录
            base_path = sys._MEIPASS
        else:
            # 直接运行exe文件
            base_path = os.path.dirname(sys.executable)
    else:
        # 开发环境
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_resource_path("assets/logo.ico")))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
import sys

from views.mainwindow import MainWindow
from utils.path_utils import get_resource_path

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_resource_path("assets/logo.ico")))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

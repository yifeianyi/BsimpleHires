from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
import sys
from views.mainwindow import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/logo.ico"))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

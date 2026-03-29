from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
import sys

from views.mainwindow import MainWindow
from utils.logging_utils import setup_logging, get_logger
from utils.path_utils import get_resource_path

if __name__ == "__main__":
    log_file = setup_logging()
    logger = get_logger(__name__)
    logger.info("应用启动，日志文件: %s", log_file)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_resource_path("assets/logo.ico")))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

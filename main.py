import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from utils.logging_utils import get_logger, setup_logging
from utils.path_utils import get_resource_path
from views.mainwindow import MainWindow


if __name__ == '__main__':
    log_file = setup_logging()
    logger = get_logger(__name__)
    logger.info('?????????: %s', log_file)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_resource_path('assets/logo.ico')))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

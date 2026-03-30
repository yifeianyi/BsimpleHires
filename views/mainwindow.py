from PyQt6.QtWidgets import QWidget

from ui.UI_main import Ui_MainWindow
from utils.app_info import APP_NAME
from views.workpage import WorkPage
from views.version_dialog import VersionDialog


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.versionDialog = None

        self.workPage = None
        self.setWindowTitle(APP_NAME)
        self.ui.ImportButton.setText("导入文件")
        self.ui.VerButton.setText("版本信息")
        self.ui.ImportButton.clicked.connect(self.gotoWorkPage)
        self.ui.VerButton.clicked.connect(self.showVersionDialog)

    def gotoWorkPage(self):
        self.workPage = WorkPage()
        self.workPage.show()
        self.hide()
        self.workPage.importFiles()

    def showVersionDialog(self):
        if self.versionDialog is None:
            self.versionDialog = VersionDialog(self)

        self.versionDialog.show()
        self.versionDialog.raise_()
        self.versionDialog.activateWindow()

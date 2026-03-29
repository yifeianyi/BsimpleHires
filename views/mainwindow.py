from PyQt6.QtWidgets import QWidget

from ui.UI_main import Ui_MainWindow
from views.workpage import WorkPage


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.workPage = None
        self.ui.ImportButton.clicked.connect(self.gotoWorkPage)

    def gotoWorkPage(self):
        self.workPage = WorkPage()
        self.workPage.show()
        self.hide()
        self.workPage.importFiles()

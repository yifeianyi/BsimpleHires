# views/mainwindow.py
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget

from views.workpage import WorkPage
from ui.UI_main import Ui_MainWindow


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        # uic.loadUi("ui/main.ui", self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.workPage = None
        self.ui.ImportButton.clicked.connect(self.gotoWorkPage)
        # self.ui.VerButton.clicked.connect(self.gotoVersionPage) 

    def gotoWorkPage(self):
        # 创建 WorkPage
        self.workPage = WorkPage()

        # 先导入文件（用户从主界面点击“导入”）
        self.workPage.importFiles()

        # 再跳转
        self.workPage.show()
        self.hide()

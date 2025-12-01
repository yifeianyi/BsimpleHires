from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QApplication, QFileDialog, QTableWidgetItem, QCheckBox, QHBoxLayout, QWidget
import os
from PyQt6.QtCore import Qt


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/main.ui", self)
        self.workPage = None  # 用于保存窗口引用

    
        # 连接信号
        self.p1.clicked.connect(self.gotoWorkPage)


    def gotoWorkPage(self):
        # 创建 WorkPage 窗口
        self.workPage = WorkPage()
        self.workPage.show()
        self.hide()
        self.workPage.importFiles()

    
class WorkPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/workPage.ui", self)

        self.mainWindow = None  # 由外部注入

    def importFiles(self):
        # 打开 Windows 文件选择对话框
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.flv *.mkv);;音频文件 (*.wav *.aac *.mp3);;所有文件 (*.*)"
        )

        if not files:
            return

        for f in files:
            self.addFileToTable(f)

    def addFileToTable(self, filepath):
        row = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row)

        # (1) 勾选框
        checkbox = QCheckBox()
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tableWidget.setCellWidget(row, 0, widget)

        # (2) 文件名
        filename = os.path.basename(filepath)
        self.tableWidget.setItem(row, 1, QTableWidgetItem(filename))

        # (3) 路径
        self.tableWidget.setItem(row, 5, QTableWidgetItem(filepath))
app = QApplication([])
win = MainWindow()
win.show()
app.exec()
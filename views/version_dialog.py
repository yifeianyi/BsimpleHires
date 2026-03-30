from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFrame, QLabel, QPushButton, QVBoxLayout

from utils.app_info import (
    APP_NAME,
    APP_VERSION,
    AUTHOR_DESCRIPTION,
    AUTHOR_NAME,
    GITHUB_URL,
    XIUXIUMAN_BILIBILI_URL,
)


class VersionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("版本信息")
        self.setMinimumWidth(460)
        self.setModal(False)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel(APP_NAME, self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title_label)

        card = QFrame(self)
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        version_label = QLabel(f"版本号：{APP_VERSION}", card)
        card_layout.addWidget(version_label)

        author_label = QLabel(
            f'作者：{AUTHOR_NAME}（{AUTHOR_DESCRIPTION}）'
            f' <a href="{XIUXIUMAN_BILIBILI_URL}">咻咻满的 B 站主页</a>',
            card,
        )
        author_label.setOpenExternalLinks(True)
        author_label.setWordWrap(True)
        author_label.setTextFormat(Qt.TextFormat.RichText)
        card_layout.addWidget(author_label)

        github_label = QLabel(f'GitHub 主页：<a href="{GITHUB_URL}">{GITHUB_URL}</a>', card)
        github_label.setOpenExternalLinks(True)
        github_label.setWordWrap(True)
        github_label.setTextFormat(Qt.TextFormat.RichText)
        card_layout.addWidget(github_label)

        layout.addWidget(card)

        close_button = QPushButton("关闭", self)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

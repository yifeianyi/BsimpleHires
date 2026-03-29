from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from services.settings_service import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(520, 220)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(12)

        self.default_output_edit = QLineEdit(settings.default_output_dir, self)
        self.default_output_edit.setPlaceholderText("未设置时每次手动选择")
        form_layout.addRow(
            "默认输出目录",
            self._build_path_row(self.default_output_edit, self._choose_default_output_dir),
        )

        self.max_workers_spin = QSpinBox(self)
        self.max_workers_spin.setRange(1, 4)
        self.max_workers_spin.setValue(settings.max_workers)
        form_layout.addRow("最大并发数", self.max_workers_spin)

        self.naming_strategy_combo = QComboBox(self)
        self.naming_strategy_combo.addItem("自动递增避免覆盖", "auto_increment")
        self.naming_strategy_combo.addItem("直接覆盖同名输出", "overwrite")
        self._set_combo_value(self.naming_strategy_combo, settings.naming_strategy)
        form_layout.addRow("输出命名策略", self.naming_strategy_combo)

        self.open_output_checkbox = QCheckBox("转换完成后自动打开输出目录", self)
        self.open_output_checkbox.setChecked(settings.open_output_dir_after_completion)
        form_layout.addRow(QLabel("完成后动作", self), self.open_output_checkbox)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _build_path_row(self, line_edit: QLineEdit, handler) -> QWidget:
        container = QWidget(self)
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        button = QPushButton("浏览", container)
        button.clicked.connect(handler)
        row_layout.addWidget(line_edit, 1)
        row_layout.addWidget(button)
        return container

    def _choose_default_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "选择默认输出目录",
            self.default_output_edit.text().strip(),
            QFileDialog.Option.ShowDirsOnly,
        )
        if path:
            self.default_output_edit.setText(path)

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    def get_settings(self) -> AppSettings:
        return AppSettings(
            default_output_dir=self.default_output_edit.text().strip(),
            max_workers=self.max_workers_spin.value(),
            naming_strategy=self.naming_strategy_combo.currentData(),
            open_output_dir_after_completion=self.open_output_checkbox.isChecked(),
        )

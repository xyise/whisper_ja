from __future__ import annotations

from PySide6 import QtWidgets


class ControlWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Whisper Subtitle App")
        self.resize(520, 220)

        central = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(central)
        form = QtWidgets.QFormLayout()

        self.app_combo = QtWidgets.QComboBox(self)
        self.model_combo = QtWidgets.QComboBox(self)
        self.model_combo.addItems(["tiny", "base", "small", "medium"])
        self.model_combo.setCurrentText("small")
        self.language_edit = QtWidgets.QLineEdit("ja", self)
        self.language_edit.setPlaceholderText("ja, en, auto...")
        form.addRow("Video app", self.app_combo)
        form.addRow("Whisper model", self.model_combo)
        form.addRow("Language", self.language_edit)
        layout.addLayout(form)

        button_row = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton("Refresh apps", self)
        self.start_button = QtWidgets.QPushButton("Start", self)
        self.stop_button = QtWidgets.QPushButton("Stop", self)
        self.stop_button.setEnabled(False)
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        layout.addLayout(button_row)

        self.status_label = QtWidgets.QLabel("Ready", self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.setCentralWidget(central)

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class SubtitleWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Live Subtitles")
        self.resize(700, 260)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)

        self._text_edit = QtWidgets.QTextEdit(self)
        self._text_edit.setReadOnly(True)
        self._text_edit.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard
        )
        self._text_edit.setPlaceholderText("Subtitles will appear here...")
        self._text_edit.setStyleSheet("font-size: 20px; padding: 12px;")
        self.setCentralWidget(self._text_edit)

    def set_subtitles(self, text: str) -> None:
        self._text_edit.setPlainText(text)
        cursor = self._text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._text_edit.setTextCursor(cursor)

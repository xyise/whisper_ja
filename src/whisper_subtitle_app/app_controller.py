from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from .capture.bridge import NativeBridge, NativeBridgeError
from .models import AppSource
from .subtitle_buffer import SubtitleBuffer
from .transcription.engine import LocalTranscriptionSession, TranscriptionConfig
from .ui.control_window import ControlWindow
from .ui.subtitle_window import SubtitleWindow


class AppController(QtCore.QObject):
    subtitle_received = QtCore.Signal(str)
    status_changed = QtCore.Signal(str)
    error_raised = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.control_window = ControlWindow()
        self.subtitle_window = SubtitleWindow()
        self.subtitle_buffer = SubtitleBuffer()
        self.bridge = NativeBridge()
        self._apps: list[AppSource] = []
        self._session: LocalTranscriptionSession | None = None

        self.subtitle_received.connect(self._on_subtitle_received)
        self.status_changed.connect(self.control_window.status_label.setText)
        self.error_raised.connect(self._show_error)

        self.control_window.refresh_button.clicked.connect(self.refresh_apps)
        self.control_window.start_button.clicked.connect(self.start_capture)
        self.control_window.stop_button.clicked.connect(self.stop_capture)

    def show(self) -> None:
        self.control_window.show()
        self.subtitle_window.show()
        self.refresh_apps()

    @QtCore.Slot()
    def refresh_apps(self) -> None:
        try:
            self.status_changed.emit("Loading captureable apps...")
            self._apps = self.bridge.list_apps()
            self.control_window.app_combo.clear()
            for app in self._apps:
                self.control_window.app_combo.addItem(app.label, userData=app)
            if not self._apps:
                self.status_changed.emit("No captureable apps found")
                return
            self.status_changed.emit(f"Loaded {len(self._apps)} captureable apps")
        except NativeBridgeError as exc:
            self.error_raised.emit(str(exc))

    @QtCore.Slot()
    def start_capture(self) -> None:
        current_app = self.control_window.app_combo.currentData()
        if not isinstance(current_app, AppSource):
            self.error_raised.emit("Choose a video app before starting capture")
            return

        self.stop_capture()
        self.subtitle_buffer.clear()
        self.subtitle_window.set_subtitles("")
        self.control_window.start_button.setEnabled(False)
        self.control_window.stop_button.setEnabled(True)

        language = self.control_window.language_edit.text().strip() or None
        config = TranscriptionConfig(
            model_name=self.control_window.model_combo.currentText(),
            language=language,
        )
        self._session = LocalTranscriptionSession(
            source=current_app,
            config=config,
            on_subtitle=self.subtitle_received.emit,
            on_status=self.status_changed.emit,
            on_error=self.error_raised.emit,
        )
        self._session.start()

    @QtCore.Slot()
    def stop_capture(self) -> None:
        if self._session is not None:
            self._session.stop()
            self._session = None
        self.control_window.start_button.setEnabled(True)
        self.control_window.stop_button.setEnabled(False)
        self.status_changed.emit("Ready")

    @QtCore.Slot(str)
    def _on_subtitle_received(self, text: str) -> None:
        if self.subtitle_buffer.add_line(text):
            self.subtitle_window.set_subtitles(self.subtitle_buffer.to_display_text())

    @QtCore.Slot(str)
    def _show_error(self, message: str) -> None:
        self.control_window.start_button.setEnabled(True)
        self.control_window.stop_button.setEnabled(False)
        self.status_changed.emit("Error")
        QtWidgets.QMessageBox.critical(self.control_window, "Whisper Subtitle App", message)

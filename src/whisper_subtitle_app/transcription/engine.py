from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from typing import Callable

import numpy as np

from ..capture.bridge import NativeBridge, NativeBridgeError
from ..models import AppSource

SubtitleCallback = Callable[[str], None]
StatusCallback = Callable[[str], None]
ErrorCallback = Callable[[str], None]


@dataclass(slots=True)
class TranscriptionConfig:
    model_name: str = "small"
    language: str | None = "ja"
    sample_rate: int = 16_000
    chunk_seconds: int = 4


class LocalTranscriptionSession:
    def __init__(
        self,
        source: AppSource,
        config: TranscriptionConfig,
        on_subtitle: SubtitleCallback,
        on_status: StatusCallback,
        on_error: ErrorCallback,
    ) -> None:
        self._source = source
        self._config = config
        self._on_subtitle = on_subtitle
        self._on_status = on_status
        self._on_error = on_error
        self._bridge = NativeBridge()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Transcription session already started")
        self._thread = threading.Thread(target=self._run, name="transcription-session", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._process and self._process.poll() is None:
            self._process.terminate()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        try:
            self._on_status("Building native capture helper...")
            self._process = self._bridge.start_capture(self._source, sample_rate=self._config.sample_rate)
            from faster_whisper import WhisperModel

            self._on_status("Loading Whisper model...")
            model = WhisperModel(self._config.model_name, device="auto", compute_type="auto")
            self._on_status(f"Capturing audio from {self._source.name}...")

            chunk_bytes = self._config.sample_rate * self._config.chunk_seconds * 4
            stdout = self._bridge.stream(self._process)
            last_text = ""

            while not self._stop_event.is_set():
                raw = stdout.read(chunk_bytes)
                if not raw:
                    break
                if len(raw) < 4:
                    continue

                audio = np.frombuffer(raw, dtype=np.float32)
                if audio.size == 0:
                    continue

                segments, _ = model.transcribe(
                    audio,
                    language=self._config.language,
                    vad_filter=True,
                    beam_size=1,
                    best_of=1,
                    condition_on_previous_text=False,
                )
                lines = [segment.text.strip() for segment in segments if segment.text.strip()]
                for line in lines:
                    if line == last_text:
                        continue
                    last_text = line
                    self._on_subtitle(line)

            if self._process and self._process.poll() not in (None, 0) and not self._stop_event.is_set():
                stderr_text = self._bridge.read_stderr_text(self._process).strip()
                raise NativeBridgeError(stderr_text or "Native capture helper exited unexpectedly")

            self._on_status("Stopped")
        except (ImportError, NativeBridgeError, OSError, RuntimeError, ValueError) as exc:
            self._on_error(str(exc))
            self._on_status("Error")

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import BinaryIO

from ..models import AppSource


class NativeBridgeError(RuntimeError):
    pass


class NativeBridge:
    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self._root = root
        self._helper_source = root / "src" / "whisper_subtitle_app" / "capture" / "helper_bridge.swift"
        self._helper_binary = root / ".build" / "whisper_subtitle_bridge"

    def ensure_built(self) -> Path:
        self._helper_binary.parent.mkdir(parents=True, exist_ok=True)
        if self._helper_binary.exists() and self._helper_binary.stat().st_mtime >= self._helper_source.stat().st_mtime:
            return self._helper_binary

        command = [
            "xcrun",
            "swiftc",
            "-O",
            "-parse-as-library",
            "-o",
            str(self._helper_binary),
            str(self._helper_source),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "unknown swiftc error"
            raise NativeBridgeError(f"Failed to build native capture helper: {message}")
        return self._helper_binary

    def list_apps(self) -> list[AppSource]:
        binary = self.ensure_built()
        completed = subprocess.run([str(binary), "list-apps"], capture_output=True, text=True)
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "helper failed"
            raise NativeBridgeError(f"Failed to list captureable apps: {message}")

        try:
            items = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise NativeBridgeError("Native helper returned invalid app JSON") from exc

        apps = [
            AppSource(
                name=item["name"],
                bundle_identifier=item["bundleIdentifier"],
                process_id=int(item["processId"]),
            )
            for item in items
        ]
        return [app for app in apps if app.bundle_identifier]

    def start_capture(self, source: AppSource, sample_rate: int = 16_000) -> subprocess.Popen[bytes]:
        binary = self.ensure_built()
        process = subprocess.Popen(
            [
                str(binary),
                "capture",
                "--bundle-id",
                source.bundle_identifier,
                "--sample-rate",
                str(sample_rate),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if process.stdout is None:
            raise NativeBridgeError("Native helper did not expose stdout for audio capture")
        return process

    @staticmethod
    def read_stderr_text(process: subprocess.Popen[bytes]) -> str:
        if process.stderr is None:
            return ""
        return process.stderr.read().decode("utf-8", errors="replace")

    @staticmethod
    def stream(process: subprocess.Popen[bytes]) -> BinaryIO:
        if process.stdout is None:
            raise NativeBridgeError("Native helper stdout is unavailable")
        return process.stdout

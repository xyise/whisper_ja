from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from .models import SubtitleLine


@dataclass(slots=True)
class SubtitleBufferConfig:
    max_lines: int = 8


class SubtitleBuffer:
    def __init__(self, config: SubtitleBufferConfig | None = None) -> None:
        self._config = config or SubtitleBufferConfig()
        self._lines: deque[SubtitleLine] = deque(maxlen=self._config.max_lines)
        self._last_normalized_text = ""

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.strip().split()).casefold()

    def add_line(self, text: str) -> bool:
        normalized = self._normalize(text)
        if not normalized or normalized == self._last_normalized_text:
            return False
        line = SubtitleLine(text=text.strip())
        self._lines.append(line)
        self._last_normalized_text = normalized
        return True

    def clear(self) -> None:
        self._lines.clear()
        self._last_normalized_text = ""

    def lines(self) -> list[SubtitleLine]:
        return list(self._lines)

    def extend(self, values: Iterable[str]) -> int:
        added = 0
        for value in values:
            added += int(self.add_line(value))
        return added

    def to_display_text(self) -> str:
        return "\n".join(line.text for line in self._lines)

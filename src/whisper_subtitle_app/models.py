from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass(slots=True)
class AppSource:
    name: str
    bundle_identifier: str
    process_id: int

    @property
    def label(self) -> str:
        return f"{self.name} ({self.bundle_identifier})"


@dataclass(slots=True)
class SubtitleLine:
    text: str
    created_at: float = field(default_factory=time)

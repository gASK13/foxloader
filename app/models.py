from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True, frozen=True)
class TargetOption:
    label: str
    relative_path: str
    depth: int
    is_default: bool = False


@dataclass(slots=True, frozen=True)
class ParsedMedia:
    is_series: bool
    season_number: int | None = None

    @property
    def season_folder_name(self) -> str | None:
        if self.season_number is None:
            return None
        return f"Season {self.season_number:02d}"


@dataclass(slots=True, frozen=True)
class TargetResolution:
    base_relative_path: str
    season_subdir: str | None
    final_relative_path: str
    absolute_path: Path


@dataclass(slots=True)
class QueueItem:
    id: str
    name: str
    status: str
    bytes_total: int | None
    bytes_loaded: int | None
    speed_bps: int | None
    progress_percent: float
    target_path: str | None = None
    package_name: str | None = None
    finished_at: datetime | None = None
    source: str = "active"
    eta_seconds: int | None = None


@dataclass(slots=True)
class QueueSnapshot:
    active: list[QueueItem] = field(default_factory=list)
    waiting: list[QueueItem] = field(default_factory=list)
    completed: list[QueueItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SubmissionResult:
    accepted_links: int
    target_paths: list[str]
    messages: list[str] = field(default_factory=list)

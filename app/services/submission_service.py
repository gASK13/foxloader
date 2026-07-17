from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from app.models import SubmissionResult
from app.services.folder_service import FolderService
from app.services.jd_client import LocalJdClient
from app.services.parser_service import detect_media


class SubmissionService:
    def __init__(self, folder_service: FolderService, client: LocalJdClient) -> None:
        self.folder_service = folder_service
        self.client = client

    def submit_links(self, raw_links: str, selected_target: str) -> SubmissionResult:
        links = self._normalize_links(raw_links)
        if not links:
            raise ValueError("No links were provided.")

        grouped_links: dict[str, list[str]] = defaultdict(list)
        target_messages: list[str] = []

        for link in links:
            parsed = detect_media(link)
            resolution = self.folder_service.resolve_target(selected_target, parsed)
            grouped_links[str(resolution.absolute_path)].append(link)
            target_messages.append(f"{link} -> {resolution.final_relative_path}")

        target_paths = sorted(grouped_links.keys())
        for absolute_target, grouped in grouped_links.items():
            package_name = Path(absolute_target).name
            self.client.add_links(grouped, absolute_target, package_name=package_name)

        return SubmissionResult(
            accepted_links=len(links),
            target_paths=target_paths,
            messages=target_messages,
        )

    @staticmethod
    def _normalize_links(raw_links: str) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for line in (raw_links or "").splitlines():
            candidate = line.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
        return normalized

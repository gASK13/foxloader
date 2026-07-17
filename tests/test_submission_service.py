from pathlib import Path

from app.config import AppConfig, JdLocalConfig
from app.models import QueueItem
from app.services.folder_service import FolderService
from app.services.submission_service import SubmissionService


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str, str | None]] = []

    def add_links(self, links: list[str], destination_folder: str, package_name: str | None = None) -> None:
        self.calls.append((links, destination_folder, package_name))

    def fetch_queue_items(self) -> list[QueueItem]:
        return []


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        download_root=tmp_path / "downloads",
        default_target="incoming",
        queue_refresh_seconds=5,
        app_host="127.0.0.1",
        app_port=8080,
        jd_local=JdLocalConfig(
            base_url="http://127.0.0.1:3129",
            request_timeout_seconds=15,
        ),
    )


def test_submission_groups_by_resolved_target(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    folder_service = FolderService(config)
    client = FakeClient()
    service = SubmissionService(folder_service, client)  # type: ignore[arg-type]

    result = service.submit_links(
        "\n".join(
            [
                "https://example.com/Futurama.S01E01.1080p.mkv",
                "https://example.com/Futurama.S01E02.1080p.mkv",
                "https://example.com/movie.mp4",
            ]
        ),
        "serialy/Futurama",
    )

    assert result.accepted_links == 3
    assert len(client.calls) == 2
    assert any("Season 01" in call[1] for call in client.calls)

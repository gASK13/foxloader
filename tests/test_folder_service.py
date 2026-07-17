from pathlib import Path

from app.config import AppConfig, JdLocalConfig
from app.models import ParsedMedia
from app.services.folder_service import FolderService, FolderValidationError


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


def test_scan_target_options_limits_depth(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    root = config.download_root
    (root / "movies").mkdir(parents=True)
    (root / "serialy" / "Futurama").mkdir(parents=True)
    (root / "serialy" / "Futurama" / "Season 01").mkdir(parents=True)

    service = FolderService(config)
    options = service.scan_target_options()
    values = {option.relative_path for option in options}

    assert "incoming" in values
    assert "movies" in values
    assert "serialy" in values
    assert "serialy/Futurama" in values
    assert "serialy/Futurama/Season 01" not in values


def test_validate_target_rejects_deep_paths(tmp_path: Path) -> None:
    service = FolderService(make_config(tmp_path))

    try:
        service.validate_target("a/b/c")
    except FolderValidationError as exc:
        assert "2 levels" in str(exc)
    else:
        raise AssertionError("Expected FolderValidationError")


def test_resolve_target_adds_season_folder(tmp_path: Path) -> None:
    service = FolderService(make_config(tmp_path))
    parsed = ParsedMedia(is_series=True, season_number=1)

    resolution = service.resolve_target("serialy/Futurama", parsed)

    assert resolution.season_subdir == "Season 01"
    assert resolution.final_relative_path == "serialy/Futurama/Season 01"
    assert resolution.absolute_path.exists()

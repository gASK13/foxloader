from __future__ import annotations

from pathlib import Path

from app.config import AppConfig
from app.models import ParsedMedia, TargetOption, TargetResolution


class FolderValidationError(ValueError):
    """Raised when a target path is invalid or unsafe."""


class FolderService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def ensure_root_exists(self) -> None:
        self.config.download_root.mkdir(parents=True, exist_ok=True)

    def scan_target_options(self) -> list[TargetOption]:
        self.ensure_root_exists()
        options: list[TargetOption] = [
            TargetOption(
                label=f"Default ({self.config.default_target})",
                relative_path=self.config.default_target,
                depth=len(self._split_relative(self.config.default_target)),
                is_default=True,
            )
        ]
        seen = {self.config.default_target}

        for first_level in sorted(self.config.download_root.iterdir(), key=lambda item: item.name.lower()):
            if not first_level.is_dir():
                continue
            relative_first = first_level.relative_to(self.config.download_root).as_posix()
            if relative_first not in seen:
                options.append(
                    TargetOption(
                        label=relative_first,
                        relative_path=relative_first,
                        depth=1,
                        is_default=False,
                    )
                )
                seen.add(relative_first)

            for second_level in sorted(first_level.iterdir(), key=lambda item: item.name.lower()):
                if not second_level.is_dir():
                    continue
                relative_second = second_level.relative_to(self.config.download_root).as_posix()
                if relative_second not in seen:
                    options.append(
                        TargetOption(
                            label=relative_second,
                            relative_path=relative_second,
                            depth=2,
                            is_default=False,
                        )
                    )
                    seen.add(relative_second)

        return options

    def validate_target(self, relative_path: str) -> str:
        normalized = (relative_path or "").strip().replace("\\", "/").strip("/")
        if not normalized:
            raise FolderValidationError("Target folder must not be empty.")
        parts = self._split_relative(normalized)
        if len(parts) > 2:
            raise FolderValidationError("Only folders up to 2 levels under the root are allowed.")
        candidate = (self.config.download_root / Path(*parts)).resolve()
        if not self._is_within_root(candidate):
            raise FolderValidationError("Target folder escapes the configured root.")
        return Path(*parts).as_posix()

    def resolve_target(self, selected_target: str, parsed_media: ParsedMedia) -> TargetResolution:
        base_relative = self.validate_target(selected_target)
        base_path = (self.config.download_root / Path(base_relative)).resolve()

        season_subdir = parsed_media.season_folder_name if parsed_media.is_series else None
        final_path = base_path
        final_relative = base_relative
        if season_subdir:
            final_path = (base_path / season_subdir).resolve()
            final_relative = Path(base_relative, season_subdir).as_posix()

        if not self._is_within_root(final_path):
            raise FolderValidationError("Resolved download path escapes the configured root.")

        final_path.mkdir(parents=True, exist_ok=True)
        return TargetResolution(
            base_relative_path=base_relative,
            season_subdir=season_subdir,
            final_relative_path=final_relative,
            absolute_path=final_path,
        )

    def _is_within_root(self, path: Path) -> bool:
        try:
            path.relative_to(self.config.download_root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _split_relative(relative_path: str) -> list[str]:
        parts = [part for part in relative_path.split("/") if part]
        if any(part in {".", ".."} for part in parts):
            raise FolderValidationError("Relative target path contains an unsafe segment.")
        return parts

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when application configuration is invalid."""


@dataclass(slots=True, frozen=True)
class JdLocalConfig:
    base_url: str
    request_timeout_seconds: int


@dataclass(slots=True, frozen=True)
class AppConfig:
    download_root: Path
    default_target: str
    queue_refresh_seconds: int
    app_host: str
    app_port: int
    jd_local: JdLocalConfig


def load_config(
    config_path: str | Path = "config.yaml",
    env_path: str | Path = ".env",
) -> AppConfig:
    load_dotenv(env_path, override=False)

    path = Path(config_path)
    if not path.exists():
        raise ConfigError(
            f"Configuration file '{path}' was not found. Copy config.example.yaml to config.yaml."
        )

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    download_root = Path(data.get("download_root", "./downloads")).expanduser().resolve()
    default_target = _normalize_relative_target(data.get("default_target", "incoming"))

    queue_refresh_seconds = int(data.get("queue_refresh_seconds", 5))
    if queue_refresh_seconds < 2:
        raise ConfigError("queue_refresh_seconds must be >= 2")

    app_host = str(data.get("app_host", "127.0.0.1"))
    app_port = int(data.get("app_port", 8080))
    jd_base_url = str(os.getenv("JD_BASE_URL", data.get("jd_base_url", "http://127.0.0.1:3129"))).strip()
    jd_request_timeout_seconds = int(
        os.getenv("JD_REQUEST_TIMEOUT_SECONDS", data.get("jd_request_timeout_seconds", 15))
    )
    if jd_request_timeout_seconds < 1:
        raise ConfigError("jd_request_timeout_seconds must be >= 1")

    _validate_target_depth(default_target)

    return AppConfig(
        download_root=download_root,
        default_target=default_target,
        queue_refresh_seconds=queue_refresh_seconds,
        app_host=app_host,
        app_port=app_port,
        jd_local=JdLocalConfig(
            base_url=_normalize_base_url(jd_base_url),
            request_timeout_seconds=jd_request_timeout_seconds,
        ),
    )


def _normalize_relative_target(value: str) -> str:
    value = str(value or "").strip().replace("\\", "/").strip("/")
    if not value:
        raise ConfigError("default_target must not be empty")
    if value == ".":
        raise ConfigError("default_target must point to a folder under the root")
    return value


def _validate_target_depth(relative_path: str) -> None:
    parts = [part for part in relative_path.split("/") if part]
    if len(parts) > 2:
        raise ConfigError("target paths may be at most 2 levels deep under download_root")
    if any(part in {"..", "."} for part in parts):
        raise ConfigError("target paths may not contain '.' or '..'")


def _normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise ConfigError("jd_base_url must start with http:// or https://")
    return normalized

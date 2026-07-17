from __future__ import annotations

from typing import Any

import requests

from app.config import JdLocalConfig
from app.models import QueueItem


class JdClientError(RuntimeError):
    """Raised when the JDownloader integration fails."""


class LocalJdClient:
    def __init__(self, config: JdLocalConfig, session: requests.Session | None = None) -> None:
        self.config = config
        self._session = session or requests.Session()

    def connect(self) -> None:
        self._request("GET", "/jdcheckjson")

    def add_links(self, links: list[str], destination_folder: str, package_name: str | None = None) -> Any:
        if not links:
            raise JdClientError("No links provided.")

        payload = [
            {
                "autostart": True,
                "links": "\n".join(links),
                "packageName": package_name,
                "destinationFolder": destination_folder,
                "overwritePackagizerRules": True,
            }
        ]
        return self._request("POST", "/linkgrabberv2/addLinks", json=payload)

    def fetch_queue_items(self) -> list[QueueItem]:
        records = self._query_download_links()
        items = [self._map_queue_item(record) for record in records]
        return [item for item in items if item is not None]

    def _query_download_links(self) -> list[dict[str, Any]]:
        query = {
            "name": True,
            "bytesLoaded": True,
            "bytesTotal": True,
            "eta": True,
            "speed": True,
            "status": True,
            "enabled": True,
            "packageUUIDs": [],
            "saveTo": True,
            "packageName": True,
            "uuid": True,
        }
        result = self._request("POST", "/downloadsV2/queryLinks", json=[query])
        return list(result or [])

    def _map_queue_item(self, record: dict[str, Any]) -> QueueItem | None:
        item_id = record.get("uuid") or record.get("id")
        if item_id is None:
            return None

        bytes_total = self._safe_int(record.get("bytesTotal"))
        bytes_loaded = self._safe_int(record.get("bytesLoaded"))
        progress = 0.0
        if bytes_total and bytes_total > 0 and bytes_loaded is not None:
            progress = round((bytes_loaded / bytes_total) * 100, 1)

        return QueueItem(
            id=str(item_id),
            name=str(record.get("name") or record.get("packageName") or f"Item {item_id}"),
            status=str(record.get("status") or "UNKNOWN"),
            bytes_total=bytes_total,
            bytes_loaded=bytes_loaded,
            speed_bps=self._safe_int(record.get("speed")),
            progress_percent=progress,
            target_path=record.get("saveTo"),
            package_name=record.get("packageName"),
            eta_seconds=self._safe_int(record.get("eta")),
        )

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _request(self, method: str, path: str, json: Any | None = None) -> Any:
        url = f"{self.config.base_url}{path}"
        try:
            response = self._session.request(
                method=method,
                url=url,
                json=json,
                timeout=self.config.request_timeout_seconds,
            )
        except requests.RequestException as exc:  # pragma: no cover
            raise JdClientError(f"Local JD2 API request failed for {url}: {exc}") from exc

        if response.status_code >= 400:
            raise JdClientError(f"Local JD2 API returned HTTP {response.status_code} for {path}")

        if not response.content:
            return None

        try:
            return response.json()
        except ValueError:
            return response.text

from __future__ import annotations

import json as jsonlib
import logging
from urllib.parse import quote
from typing import Any

import requests

from app.config import JdLocalConfig
from app.models import QueueItem


class JdClientError(RuntimeError):
    """Raised when the JDownloader integration fails."""


logger = logging.getLogger(__name__)


class LocalJdClient:
    def __init__(self, config: JdLocalConfig, session: requests.Session | None = None) -> None:
        self.config = config
        self._session = session or requests.Session()

    def connect(self) -> None:
        logger.info("Checking JD2 API availability at %s", self.config.base_url)
        self._request("GET", "/jdcheckjson")

    def add_links(self, links: list[str], destination_folder: str, package_name: str | None = None) -> Any:
        if not links:
            raise JdClientError("No links provided.")

        logger.info(
            "Submitting %s link(s) to JD2 target=%s package=%s",
            len(links),
            destination_folder,
            package_name or "",
        )
        joined_links = "\n".join(links)
        add_links_query = [
            {
                "assignJobID": True,
                "autostart": True,
                "links": joined_links,
                "packageName": package_name,
                "destinationFolder": destination_folder,
                "overwritePackagizerRules": True,
            }
        ]
        try:
            return self._request_with_raw_query(
                "GET",
                "/linkgrabberv2/addLinks",
                add_links_query[0],
            )
        except JdClientError as exc:
            logger.warning("linkgrabberv2/addLinks failed, trying legacy fallback: %s", exc)
            return self._request_with_legacy_args(
                "GET",
                "/linkcollector/addLinks",
                [
                    joined_links,
                    package_name or "",
                    None,
                    None,
                    destination_folder,
                ],
            )

    def fetch_queue_items(self) -> list[QueueItem]:
        logger.info("Polling JD2 download queue")
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
        result = self._request_with_raw_query("GET", "/downloadsV2/queryLinks", query)
        return self._extract_records(result)

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
        logger.info("JD2 request %s %s", method, url)
        try:
            response = self._session.request(
                method=method,
                url=url,
                json=json,
                timeout=self.config.request_timeout_seconds,
            )
        except requests.RequestException as exc:  # pragma: no cover
            logger.exception("JD2 request transport failure: %s %s", method, url)
            raise JdClientError(f"Local JD2 API request failed for {url}: {exc}") from exc

        logger.info("JD2 response %s %s -> HTTP %s", method, url, response.status_code)
        if response.status_code >= 400:
            body = (response.text or "").strip()
            logger.error("JD2 error response for %s %s: %s", method, url, body[:500] if body else "<empty>")
            details = f": {body[:300]}" if body else ""
            raise JdClientError(f"Local JD2 API returned HTTP {response.status_code} for {path}{details}")

        if not response.content:
            return None

        try:
            return response.json()
        except ValueError:
            return response.text

    def _request_with_raw_query(self, method: str, path: str, query_object: Any) -> Any:
        raw_query = quote(jsonlib.dumps(query_object, separators=(",", ":")), safe="")
        return self._request(method, f"{path}?{raw_query}")

    def _request_with_legacy_args(self, method: str, path: str, args: list[Any]) -> Any:
        encoded_args = []
        for arg in args:
            encoded_args.append(quote(jsonlib.dumps(arg, separators=(",", ":")), safe=""))
        return self._request(method, f"{path}?{'&'.join(encoded_args)}")

    @staticmethod
    def _extract_records(result: Any) -> list[dict[str, Any]]:
        if result is None:
            return []
        if isinstance(result, dict):
            data = result.get("data", [])
            if isinstance(data, list):
                return [record for record in data if isinstance(record, dict)]
            return []
        if isinstance(result, list):
            return [record for record in result if isinstance(record, dict)]
        return []

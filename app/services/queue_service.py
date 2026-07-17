from __future__ import annotations

from datetime import datetime
import logging

from app.models import QueueItem, QueueSnapshot
from app.services.jd_client import JdClientError, LocalJdClient


logger = logging.getLogger(__name__)


class QueueService:
    COMPLETED_STATUSES = {
        "FINISHED",
        "COMPLETED",
        "EXTRACTION_OK",
    }
    WAITING_KEYWORDS = ("QUEUE", "WAIT", "PENDING")

    def __init__(self, client: LocalJdClient) -> None:
        self.client = client
        self._completed: dict[str, QueueItem] = {}

    def get_snapshot(self) -> QueueSnapshot:
        try:
            items = self.client.fetch_queue_items()
        except JdClientError as exc:
            logger.error("Queue polling failed: %s", exc)
            return QueueSnapshot(errors=[str(exc)])

        active: list[QueueItem] = []
        waiting: list[QueueItem] = []

        for item in items:
            normalized = item.status.upper()
            if normalized in self.COMPLETED_STATUSES or item.progress_percent >= 100:
                item.source = "completed"
                item.finished_at = item.finished_at or datetime.now()
                self._completed[item.id] = item
                continue

            if any(keyword in normalized for keyword in self.WAITING_KEYWORDS):
                item.source = "waiting"
                waiting.append(item)
            else:
                item.source = "active"
                active.append(item)

        completed = sorted(
            self._completed.values(),
            key=lambda item: item.finished_at or datetime.min,
            reverse=True,
        )
        logger.info(
            "Queue snapshot prepared: active=%s waiting=%s completed=%s",
            len(active),
            len(waiting),
            len(completed),
        )
        return QueueSnapshot(active=active, waiting=waiting, completed=completed)

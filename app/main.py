from __future__ import annotations

import logging
import sys

from nicegui import ui

from app.config import ConfigError, load_config
from app.ui.pages import register_main_page


logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )


def run() -> None:
    configure_logging()
    try:
        config = load_config()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        raise SystemExit(str(exc)) from exc

    logger.info(
        "Starting Downloader MVP on %s:%s with JD2 API %s",
        config.app_host,
        config.app_port,
        config.jd_local.base_url,
    )
    register_main_page(config)
    ui.run(
        host=config.app_host,
        port=config.app_port,
        title="Downloader MVP",
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()

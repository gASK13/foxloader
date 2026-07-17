from __future__ import annotations

from nicegui import ui

from app.config import ConfigError, load_config
from app.ui.pages import register_main_page


def run() -> None:
    try:
        config = load_config()
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc

    register_main_page(config)
    ui.run(
        host=config.app_host,
        port=config.app_port,
        title="Downloader MVP",
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()

from __future__ import annotations

from nicegui import ui

from app.config import AppConfig
from app.models import QueueItem, TargetOption
from app.services.folder_service import FolderService, FolderValidationError
from app.services.jd_client import JdClientError, LocalJdClient
from app.services.queue_service import QueueService
from app.services.submission_service import SubmissionService


def register_main_page(config: AppConfig) -> None:
    folder_service = FolderService(config)
    client = LocalJdClient(config.jd_local)
    queue_service = QueueService(client)
    submission_service = SubmissionService(folder_service, client)

    @ui.page("/")
    async def index() -> None:
        targets = folder_service.scan_target_options()
        target_options = _to_select_options(targets)
        selected_target = config.default_target

        ui.add_head_html(
            """
            <style>
              :root {
                --panel: #fff9ef;
                --panel-strong: #f2e2c7;
                --ink: #18202b;
                --accent: #a04616;
                --bg-a: #f7f2e7;
                --bg-b: #e8efe4;
              }
              body {
                background:
                  radial-gradient(circle at top left, rgba(216, 131, 69, 0.16), transparent 28%),
                  radial-gradient(circle at top right, rgba(56, 120, 83, 0.12), transparent 24%),
                  linear-gradient(135deg, var(--bg-a), var(--bg-b));
                color: var(--ink);
              }
            </style>
            """
        )

        with ui.column().classes("w-full max-w-6xl mx-auto p-4 md:p-8 gap-6"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-1"):
                    ui.label("Downloader MVP").classes("text-4xl font-black tracking-tight")
                    ui.label("Local NiceGUI frontend pro JDownloader 2 pres direct local API").classes(
                        "text-sm opacity-70"
                    )
                ui.icon("download_for_offline").classes("text-6xl").style("color: var(--accent);")

            with ui.row().classes("w-full gap-6 items-stretch"):
                with ui.card().classes("flex-1 min-w-[320px] shadow-xl").style("background: var(--panel);"):
                    ui.label("Odeslat odkazy").classes("text-2xl font-bold")
                    link_input = ui.textarea(
                        label="Odkazy ke stazeni",
                        placeholder="Vloz jeden nebo vice odkazu, kazdy na samostatny radek",
                    ).props("autogrow outlined").classes("w-full")

                    with ui.row().classes("w-full items-end gap-3"):
                        target_select = ui.select(
                            options=target_options,
                            value=selected_target,
                            label="Cilova slozka",
                        ).props("outlined").classes("flex-1")
                        ui.button(
                            icon="refresh",
                            on_click=lambda: _reload_targets(target_select, folder_service),
                        ).props("flat round color=secondary").tooltip("Rescan slozek pod rootem")

                    ui.label(
                        f"Root: {config.download_root} | Povolena hloubka: max. 2 urovne pod rootem"
                    ).classes("text-xs opacity-70")
                    result_box = ui.markdown("").classes("w-full text-sm")

                    async def submit() -> None:
                        try:
                            result = submission_service.submit_links(link_input.value or "", target_select.value)
                        except (ValueError, FolderValidationError, JdClientError) as exc:
                            ui.notify(str(exc), type="negative")
                            result_box.set_content(f"**Chyba:** {exc}")
                            return

                        details = "\n".join(f"- `{message}`" for message in result.messages[:10])
                        if len(result.messages) > 10:
                            details += "\n- `...`"

                        result_box.set_content(
                            "\n".join(
                                [
                                    f"**Prijato odkazu:** {result.accepted_links}",
                                    f"**Cile:** {', '.join(f'`{path}`' for path in result.target_paths)}",
                                    details,
                                ]
                            )
                        )
                        link_input.set_value("")
                        ui.notify(f"Odeslano {result.accepted_links} odkazu do JDownloaderu", type="positive")
                        queue_view.refresh()

                    ui.button("Odeslat do JDownloaderu", on_click=submit).props(
                        "color=primary unelevated"
                    ).style("background: var(--accent);")

                with ui.card().classes("w-full md:w-[360px] shadow-xl").style("background: var(--panel-strong);"):
                    ui.label("Jak to funguje").classes("text-2xl font-bold")
                    ui.markdown(
                        "\n".join(
                            [
                                "- seznam slozek se bere ze skutecneho obsahu `download_root`",
                                "- volba `Default (...)` je pevna cesta z konfigurace",
                                "- pri detekci serialu se automaticky prida `Season XX`",
                                "- cilova slozka se vytvori jeste pred odeslanim do JD2",
                                "- dokoncene polozky se drzi jen v pameti od startu aplikace",
                            ]
                        )
                    )

            @ui.refreshable
            def queue_view() -> None:
                snapshot = queue_service.get_snapshot()
                with ui.card().classes("w-full shadow-xl").style("background: rgba(255,255,255,0.82);"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("Fronta stahovani").classes("text-2xl font-bold")
                        ui.label(f"Obnovovani kazdych {config.queue_refresh_seconds}s").classes("text-xs opacity-70")

                    if snapshot.errors:
                        for error in snapshot.errors:
                            ui.label(error).classes("text-red-700 font-medium")
                        return

                    _render_queue_section("Aktivni", snapshot.active)
                    _render_queue_section("Cekajici", snapshot.waiting)
                    _render_queue_section("Dokoncene od spusteni appky", snapshot.completed)

            queue_view()
            ui.timer(config.queue_refresh_seconds, queue_view.refresh)


def _reload_targets(target_select: ui.select, folder_service: FolderService) -> None:
    options = _to_select_options(folder_service.scan_target_options())
    target_select.options = options
    if target_select.value not in options:
        target_select.value = next(iter(options))
    target_select.update()
    ui.notify("Seznam slozek byl obnoven", type="info")


def _to_select_options(targets: list[TargetOption]) -> dict[str, str]:
    return {target.relative_path: target.label for target in targets}


def _render_queue_section(title: str, items: list[QueueItem]) -> None:
    ui.separator().classes("my-2")
    with ui.column().classes("w-full gap-3"):
        ui.label(f"{title} ({len(items)})").classes("text-lg font-semibold")
        if not items:
            ui.label("Zadne polozky").classes("text-sm opacity-60 italic")
            return
        for item in items:
            with ui.card().classes("w-full shadow-sm"):
                with ui.row().classes("w-full items-start justify-between gap-4"):
                    with ui.column().classes("gap-1"):
                        ui.label(item.name).classes("text-base font-semibold")
                        ui.label(f"Stav: {item.status}").classes("text-sm")
                        if item.target_path:
                            ui.label(f"Cil: {item.target_path}").classes("text-xs opacity-70 break-all")
                    with ui.column().classes("items-end gap-1"):
                        ui.label(_format_bytes(item.bytes_loaded) + " / " + _format_bytes(item.bytes_total)).classes(
                            "text-sm"
                        )
                        ui.label(_format_speed(item.speed_bps)).classes("text-xs opacity-70")
                        if item.eta_seconds is not None:
                            ui.label(f"ETA: {_format_eta(item.eta_seconds)}").classes("text-xs opacity-70")
                ui.linear_progress(value=max(0.0, min(item.progress_percent / 100.0, 1.0))).classes("mt-2")
                ui.label(f"{item.progress_percent:.1f}%").classes("text-xs opacity-70")


def _format_bytes(value: int | None) -> str:
    if value is None:
        return "?"
    size = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _format_speed(value: int | None) -> str:
    if value is None or value <= 0:
        return "Rychlost: -"
    return f"Rychlost: {_format_bytes(value)}/s"


def _format_eta(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"

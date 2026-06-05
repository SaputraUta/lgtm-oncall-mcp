"""Vision: dashboard + panel screenshots via headless Chrome."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
from fastmcp.utilities.types import Image
from playwright.sync_api import sync_playwright

if TYPE_CHECKING:  # pragma: no cover
    from fastmcp import FastMCP

    from ..config import GrafanaConfig


@dataclass
class VisionCtx:
    grafana: httpx.Client
    cfg_grafana: GrafanaConfig


def _screenshot(url: str, token: str, viewport: tuple[int, int], full_page: bool) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": viewport[0], "height": viewport[1]},
            extra_http_headers={"Authorization": f"Bearer {token}"},
        )
        page = context.new_page()
        # IMPORTANT: do NOT use wait_until="networkidle" — Grafana keeps
        # polling for live data and never reaches idle, so playwright hangs
        # until the MCP timeout. domcontentloaded + fixed render-wait works.
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(4_000)  # let panels render
        page.keyboard.press("Escape")  # dismiss any modal (e.g. "share" dialog)
        page.wait_for_timeout(1_000)
        png = page.screenshot(full_page=full_page)
        browser.close()
    return png


def register(mcp: FastMCP, ctx: VisionCtx) -> None:
    def list_dashboards() -> list[dict]:
        """List Grafana dashboards.

        Returns [{"uid", "title", "url", "tags"}, ...].
        Call when the user asks what dashboards exist, or to find a UID
        before capture_dashboard.
        """
        r = ctx.grafana.get("/api/search", params={"type": "dash-db"})
        r.raise_for_status()
        return [
            {"uid": d["uid"], "title": d["title"], "url": d.get("url", ""), "tags": d.get("tags", [])}
            for d in r.json()
        ]

    def list_panels(dashboard_uid: str) -> list[dict]:
        """List panels in a Grafana dashboard.

        Args:
            dashboard_uid: Dashboard UID (use list_dashboards to find).

        Returns [{"id", "title", "type"}, ...].
        Call before capture_panel to find the panel id for a specific chart.
        """
        r = ctx.grafana.get(f"/api/dashboards/uid/{dashboard_uid}")
        r.raise_for_status()
        dash = r.json().get("dashboard", {})
        out: list[dict] = []

        def walk(panels: list[dict]) -> None:
            for p in panels:
                if p.get("type") == "row" and "panels" in p:
                    walk(p["panels"])
                    continue
                out.append(
                    {
                        "id": p.get("id"),
                        "title": p.get("title", ""),
                        "type": p.get("type", ""),
                    }
                )

        walk(dash.get("panels", []))
        return out

    def capture_dashboard(uid: str, env: str = "", minutes: int = 60) -> Image:
        """Screenshot a WHOLE Grafana dashboard (all panels) as a PNG.

        DO NOT call this if the user asked for a specific chart/panel
        (e.g. "error rate", "CPU"). Use list_panels + capture_panel for that.

        Args:
            uid: Dashboard UID (use list_dashboards).
            env: Template-variable value for env (default empty).
            minutes: Look-back window (default 60).
        """
        url = (
            f"{ctx.cfg_grafana.url}/d/{uid}"
            f"?from=now-{minutes}m&to=now&kiosk=tv&theme=dark"
        )
        if env:
            url += f"&var-env={env}"
        png = _screenshot(url, ctx.cfg_grafana.token, viewport=(1600, 1200), full_page=True)
        return Image(data=png, format="png")

    def capture_panel(dashboard_uid: str, panel_id: int, env: str = "", minutes: int = 60) -> Image:
        """Screenshot ONE specific panel (chart) from a dashboard as a PNG.

        Use this when the user names a specific metric — "error rate", "CPU
        chart", "latency graph". For the whole dashboard, use capture_dashboard.

        Args:
            dashboard_uid: Dashboard UID.
            panel_id: Panel id (use list_panels).
            env: Template-variable value for env (default empty).
            minutes: Look-back window (default 60).
        """
        url = (
            f"{ctx.cfg_grafana.url}/d-solo/{dashboard_uid}"
            f"?panelId={panel_id}&from=now-{minutes}m&to=now&theme=dark"
        )
        if env:
            url += f"&var-env={env}"
        png = _screenshot(url, ctx.cfg_grafana.token, viewport=(1200, 600), full_page=True)
        return Image(data=png, format="png")

    for fn in (list_dashboards, list_panels, capture_dashboard, capture_panel):
        mcp.tool(fn)

"""Serve and auto-register Lovelace resource for Child Timer card."""

from __future__ import annotations

import logging
import os
import re
import time

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.lovelace import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

_LOGGER = logging.getLogger(__name__)

URL_BASE = "/child_timer_static"
LEGACY_URL_BASE = "/quick_timer_static"  # для автообновления старого ресурса
FILENAME = "child-timer-card.js"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register HTTP view and ensure Lovelace resource exists."""

    # Register HTTP view to serve the JS
    hass.http.register_view(ChildTimerCardView())

    # Prepare URL with cache buster
    try:
        integration = await async_get_integration(hass, "child_timer")
        version = integration.version
    except Exception:  # pragma: no cover
        version = "0.0.0"

    timestamp = int(time.time())
    url = f"{URL_BASE}/{FILENAME}?v={version}&t={timestamp}"

    # Try to register/update Lovelace resource
    lovelace = hass.data.get(LOVELACE_DATA)
    if not lovelace:
        _LOGGER.debug("Lovelace not available, skipping resource registration")
        return

    resources = getattr(lovelace, "resources", None)
    if not resources:
        _LOGGER.debug(
            "Lovelace resources not available, skipping resource registration"
        )
        return

    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    installed = None
    for res in resources.async_items():
        if URL_BASE in res["url"] or LEGACY_URL_BASE in res["url"]:
            installed = res
            break

    if installed:
        if installed["url"] != url:
            _LOGGER.debug("Updating Child Timer card resource to %s", url)
            await resources.async_update_item(
                installed["id"], {"res_type": "module", "url": url}
            )
    else:
        _LOGGER.info("Creating Lovelace resource for Child Timer card")
        if getattr(resources, "async_create_item", None):
            await resources.async_create_item(
                {"res_type": "module", "url": url}
            )
        elif getattr(resources, "data", None) and getattr(
            resources.data, "append", None
        ):
            resources.data.append({"type": "module", "url": url})


class ChildTimerCardView(HomeAssistantView):
    """HTTP view to serve the card JS."""

    url = f"{URL_BASE}/{{filename}}"
    name = "child_timer:card"
    requires_auth = False

    async def get(self, request, filename):
        if filename != FILENAME:
            return web.Response(status=404, text="File not found")

        hass = request.app["hass"]
        current_dir = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(current_dir, "www", filename)

        if not await hass.async_add_executor_job(os.path.exists, file_path):
            _LOGGER.error("Card file not found: %s", file_path)
            return web.Response(status=404, text="File not found on disk")

        try:
            content = await hass.async_add_executor_job(
                self._read_file, file_path
            )

            # Inject version into CARD_VERSION constant if present
            try:
                integration = await async_get_integration(hass, "child_timer")
                file_version = integration.version or "0.0.0"
            except Exception:
                file_version = request.query.get("v") or "0.0.0"

            try:
                content = re.sub(
                    r"const\s+CARD_VERSION\s*=\s*'[^']*';",
                    f"const CARD_VERSION = '{file_version}';",
                    content,
                    count=1,
                )
            except Exception:
                _LOGGER.debug(
                    "Could not inject card version; serving original file"
                )

            return web.Response(
                body=content, content_type="application/javascript"
            )
        except Exception as exc:  # pragma: no cover
            _LOGGER.error("Error reading card file: %s", exc)
            return web.Response(status=500, text=str(exc))

    @staticmethod
    def _read_file(file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

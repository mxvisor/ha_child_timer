"""Регистрация сервисов Child Timer."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN

SERVICE_START = "start"
SERVICE_STOP = "stop"

SERVICE_SCHEMA_START = vol.Schema(
    {
        vol.Optional("duration"): vol.All(int, vol.Range(min=10)),
    }
)
SERVICE_SCHEMA_STOP = vol.Schema({})


def _get_manager(hass: HomeAssistant):
    """Возвращает единственный менеджер (single-instance интеграция)."""
    managers = hass.data.get(DOMAIN, {})
    return next(iter(managers.values()), None)


async def async_register_services(hass: HomeAssistant) -> None:
    """Регистрируем сервисы один раз."""
    if hass.services.has_service(DOMAIN, SERVICE_START):
        return

    async def handle_start(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        if manager:
            await manager.start_timer(call.data.get("duration"))

    async def handle_stop(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        if manager:
            await manager.stop_timer()

    hass.services.async_register(
        DOMAIN, SERVICE_START, handle_start, SERVICE_SCHEMA_START
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP, handle_stop, SERVICE_SCHEMA_STOP
    )

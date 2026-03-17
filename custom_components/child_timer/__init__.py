"""Child Timer Integration для Home Assistant."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, EVENT_HOMEASSISTANT_STARTED, HomeAssistant

from .const import DOMAIN
from .timer_manager import ChildTimerManager
from .services import async_register_services
from .frontend import async_register_frontend

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "button", "number", "switch", "select"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Инициализация через configuration.yaml (не используется, но обязательна)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка интеграции из Config Entry (вызывается при добавлении через UI)."""
    hass.data.setdefault(DOMAIN, {})

    manager = ChildTimerManager(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = manager

    await manager.async_setup()
    await async_register_services(hass)

    async def _register_frontend(_event=None) -> None:
        await async_register_frontend(hass)

    if hass.state == CoreState.running:
        await _register_frontend()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_frontend)

    # Регистрируем платформы sensor и button
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Удаление интеграции."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        manager: ChildTimerManager = hass.data[DOMAIN].pop(entry.entry_id)
        await manager.async_unload()
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Перезагрузка при изменении настроек."""
    await hass.config_entries.async_reload(entry.entry_id)
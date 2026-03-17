"""Button platform для Child Timer — кнопки запуска и остановки."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ChildTimerStartButton(entry, manager),
        ChildTimerStopButton(entry, manager),
    ])


class ChildTimerStartButton(ButtonEntity):
    """Запуск таймера — длительность читается из number entity."""

    def __init__(self, entry: ConfigEntry, manager) -> None:
        self.entity_id = "button.child_timer_start"
        self._manager = manager
        self._attr_unique_id = f"{entry.entry_id}_start"
        self._attr_name = "Start"
        self._attr_icon = "mdi:timer-play"

    async def async_press(self) -> None:
        await self._manager.start_timer()


class ChildTimerStopButton(ButtonEntity):
    """Остановка таймера."""

    def __init__(self, entry: ConfigEntry, manager) -> None:
        self.entity_id = "button.child_timer_stop"
        self._manager = manager
        self._attr_unique_id = f"{entry.entry_id}_stop"
        self._attr_name = "Stop"
        self._attr_icon = "mdi:timer-stop"

    async def async_press(self) -> None:
        await self._manager.stop_timer()

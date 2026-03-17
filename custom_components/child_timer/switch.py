"""Switch platform для Child Timer — включение/отключение обратного отсчёта."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([ChildTimerCountdownSwitch(entry)])


class ChildTimerCountdownSwitch(RestoreEntity, SwitchEntity):
    """Переключатель обратного отсчёта (10…1) перед завершением таймера."""

    def __init__(self, entry: ConfigEntry) -> None:
        self.entity_id = "switch.child_timer_countdown"
        self._attr_unique_id = f"{entry.entry_id}_countdown"
        self._attr_name = "Обратный отсчёт"
        self._attr_icon = "mdi:timer-10"
        self._is_on: bool = True  # включён по умолчанию

    async def async_added_to_hass(self) -> None:
        last = await self.async_get_last_state()
        if last is not None:
            self._is_on = last.state == "on"

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._is_on = False
        self.async_write_ha_state()

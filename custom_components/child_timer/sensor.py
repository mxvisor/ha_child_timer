"""Sensor platform для Child Timer — статус и оставшееся время."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Создаём сенсор для данного config entry."""
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ChildTimerSensor(entry, manager)])


class ChildTimerSensor(SensorEntity):
    """Сенсор состояния таймера (active / idle) с атрибутами остатка времени."""

    def __init__(self, entry: ConfigEntry, manager) -> None:
        self.entity_id = "sensor.child_timer"
        self._entry = entry
        self._manager = manager
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_name = "Child Timer"
        self._attr_icon = "mdi:timer"

    async def async_added_to_hass(self) -> None:
        self._manager.register_state_callback(self._on_state_changed)

    async def async_will_remove_from_hass(self) -> None:
        self._manager.unregister_state_callback(self._on_state_changed)

    @callback
    def _on_state_changed(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return "active" if self._manager.is_running else "idle"

    @property
    def extra_state_attributes(self) -> dict:
        total = self._manager._get_duration()
        remaining = self._manager.remaining_seconds
        progress = round(remaining / total, 4) if total > 0 else 0.0
        return {
            "remaining_seconds": remaining,
            "total_seconds": total,
            "remaining_formatted": self._manager.remaining_formatted,
            "progress": progress,  # 0.0..1.0 для кольца в карточке
        }

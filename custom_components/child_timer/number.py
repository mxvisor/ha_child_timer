"""Number platform для Child Timer — слайдеры длительности и интервала с сохранением состояния."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DEFAULT_DURATION


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([
        ChildTimerDurationNumber(entry),
    ])


class ChildTimerDurationNumber(NumberEntity, RestoreEntity):
    """Длительность таймера (минуты). Сохраняется между перезапусками HA."""

    def __init__(self, entry: ConfigEntry) -> None:
        self.entity_id = "number.child_timer_duration"
        self._attr_unique_id = f"{entry.entry_id}_duration"
        self._attr_name = "Длительность"
        self._attr_icon = "mdi:timer-sand"
        # Пользователь задаёт длительность в минутах: 1–1440 (сутки), шаг 1.
        self._attr_native_min_value = 1.0
        self._attr_native_max_value = 1440.0
        self._attr_native_step = 1.0
        self._attr_native_unit_of_measurement = "min"
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_value = float(DEFAULT_DURATION // 60)

    async def async_added_to_hass(self) -> None:
        last = await self.async_get_last_state()
        if last and last.state not in (None, "unknown", "unavailable"):
            try:
                self._attr_native_value = float(last.state)
            except ValueError:
                pass

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()



"""Select platform для Child Timer — выбор предустановок длительности."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_PRESET_MINUTES, DEFAULT_PRESETS
from .presets import sanitize_presets


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([ChildTimerPresetSelect(entry)])


class ChildTimerPresetSelect(SelectEntity):
    """Комбобокс с предустановками длительности."""

    _attr_icon = "mdi:timer-outline"

    def __init__(self, entry: ConfigEntry) -> None:
        self.entity_id = "select.child_timer_preset"
        self._attr_unique_id = f"{entry.entry_id}_preset_select"
        self._attr_name = "Длительность (пресет)"
        presets = sanitize_presets(entry.options.get(CONF_PRESET_MINUTES, DEFAULT_PRESETS))
        self._presets = presets
        self._attr_options = [str(v) for v in presets]

    @property
    def current_option(self) -> str | None:
        """Отобразить текущее значение, если оно совпадает с одним из пресетов."""
        state = self.hass.states.get("number.child_timer_duration")
        if not state or state.state in (None, "unknown", "unavailable"):
            return None
        try:
            minutes = float(state.state)
        except (ValueError, TypeError):
            return None
        if minutes.is_integer() and int(minutes) in self._presets:
            return str(int(minutes))
        return None

    async def async_select_option(self, option: str) -> None:
        """Установить выбранный пресет в основную длительность."""
        try:
            minutes = float(option)
        except ValueError:
            return
        if minutes not in self._presets:
            return
        await self.hass.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": "number.child_timer_duration",
                "value": minutes,
            },
            blocking=False,
        )

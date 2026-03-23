"""Switch platform для Child Timer — включение/отключение обратного отсчёта."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

# register two switches: countdown toggle and run/stop switch


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [ChildTimerCountdownSwitch(entry), ChildTimerRunSwitch(entry, manager)]
    )


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


class ChildTimerRunSwitch(SwitchEntity):
    """Единый переключатель запуска/остановки таймера."""

    def __init__(self, entry: ConfigEntry, manager) -> None:
        self._manager = manager
        self.entity_id = "switch.child_timer"
        self._attr_unique_id = f"{entry.entry_id}_running"
        self._attr_name = "Таймер"
        self._attr_icon = "mdi:timer-play"

    async def async_added_to_hass(self) -> None:
        self._manager.register_state_callback(self._on_state_changed)

    async def async_will_remove_from_hass(self) -> None:
        self._manager.unregister_state_callback(self._on_state_changed)

    def _on_state_changed(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._manager.is_running

    async def async_turn_on(self, **kwargs) -> None:
        await self._manager.start_timer()

    async def async_turn_off(self, **kwargs) -> None:
        await self._manager.stop_timer()

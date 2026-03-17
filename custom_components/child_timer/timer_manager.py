"""Менеджер таймера: нативная реализация через asyncio без timer-сущностей."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_TTS_SERVICE, CONF_MEDIA_PLAYER,
    CONF_YANDEX_STATION, CONF_ACTION_TYPE,
    ACTION_TTS, ACTION_YANDEX,
    DEFAULT_DURATION,
)

_LOGGER = logging.getLogger(__name__)


def _pluralize(n: int, one: str, few: str, many: str) -> str:
    """Русское склонение числительных."""
    if 11 <= n % 100 <= 14:
        return many
    r = n % 10
    if r == 1:
        return one
    if 2 <= r <= 4:
        return few
    return many


_COUNTDOWN_WORDS = {
    10: "Десять", 9: "Девять", 8: "Восемь", 7: "Семь",
    6: "Шесть",  5: "Пять",   4: "Четыре", 3: "Три",
    2: "Два",    1: "Один",
}


class ChildTimerManager:
    """Управляет одним экземпляром детского таймера."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._loop_task: asyncio.Task | None = None
        self._is_running: bool = False
        self._remaining: int = 0
        self._state_callbacks: list[Callable] = []

    @property
    def config(self) -> dict:
        """Актуальная конфигурация (учитывает options)."""
        return {**self.entry.data, **self.entry.options}

    def _get_duration(self) -> int:
        """Читает длительность (минуты в number) и переводит в секунды."""
        state = self.hass.states.get("number.child_timer_duration")
        if state and state.state not in ("unknown", "unavailable", None):
            try:
                minutes = float(state.state)
                return int(minutes * 60)
            except (ValueError, TypeError):
                pass
        return DEFAULT_DURATION

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def remaining_seconds(self) -> int:
        return self._remaining

    @property
    def remaining_formatted(self) -> str:
        return self._format_remaining(self._remaining)

    def register_state_callback(self, cb: Callable) -> None:
        self._state_callbacks.append(cb)

    def unregister_state_callback(self, cb: Callable) -> None:
        if cb in self._state_callbacks:
            self._state_callbacks.remove(cb)

    def _notify_state_change(self) -> None:
        for cb in self._state_callbacks:
            cb()

    async def async_setup(self) -> None:
        """Инициализация — ничего создавать не нужно, таймер запускается явно."""
        _LOGGER.info("Child Timer настроен")

    async def async_unload(self) -> None:
        """Останавливаем активный цикл при выгрузке."""
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()

    async def start_timer(self, duration: int | None = None) -> None:
        """Запускает (или перезапускает) таймер. Без аргументов читает из number entity."""
        dur = duration if duration is not None else self._get_duration()
        # Выставляем состояние ДО отмены старого таска — карточка не мигнёт в idle
        self._is_running = True
        self._remaining = dur
        self._notify_state_change()
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        self._loop_task = self.hass.async_create_task(self._run_timer(dur))
        _LOGGER.info("Child Timer запущен на %d сек", dur)
        m, s = divmod(dur, 60)
        if s == 0:
            dur_short = f"{m} мин"
        elif m == 0:
            dur_short = f"{s} сек"
        else:
            dur_short = f"{m} мин {s} сек"
        dur_full = self._format_duration_full(dur)
        try:
            await self._send_notification(
                "▶ Таймер запущен",
                f"Установлен таймер на {dur_short}",
                f"Установлен таймер на {dur_full}",
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Не удалось отправить уведомление о запуске")

    async def stop_timer(self) -> None:
        """Останавливает таймер досрочно."""
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        self._is_running = False
        self._remaining = 0
        self._notify_state_change()
        try:
            await self._send_notification("⏹ Таймер остановлен", "Таймер был отменён")
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Не удалось отправить уведомление об остановке")

    async def _run_timer(self, duration: int) -> None:
        """Основной цикл: секунды + голосовые объявления по алгоритму частоты."""
        countdown_enabled = self._is_countdown_enabled()
        _LOGGER.debug(
            "Цикл запущен: длительность=%s, countdown=%s", duration, countdown_enabled
        )

        self._is_running = True
        self._remaining = duration
        self._notify_state_change()

        try:
            for elapsed in range(1, duration + 1):
                await asyncio.sleep(1)
                self._remaining = duration - elapsed
                self._notify_state_change()

                if (
                    duration > 10
                    and countdown_enabled
                    and self._remaining in _COUNTDOWN_WORDS
                ):
                    await self._send_tts_only(_COUNTDOWN_WORDS[self._remaining])
                    continue

                if self._should_announce(self._remaining, countdown_enabled):
                    await self._send_notification(
                        "⏱ Таймер",
                        self._format_remaining(self._remaining),
                        self._format_remaining_full(self._remaining),
                    )

            self._is_running = False
            self._remaining = 0
            self._notify_state_change()
            await self._send_notification("✓ Таймер завершён", "Время истекло!", "Время вышло!")

        except asyncio.CancelledError:
            # Не сбрасываем состояние если уже запущен новый таск (перезапуск)
            if not self._is_running:
                self._remaining = 0
                self._notify_state_change()
            _LOGGER.debug("Цикл уведомлений остановлен")

    def _should_announce(self, remaining: int, countdown_enabled: bool) -> bool:
        """Частота: >1ч каждые 30 мин; 60–15 мин — каждые 15 мин;
        15–5 мин — каждые 5 мин; 5–1 мин — каждую минуту; 60–15 сек — каждые 15 сек.
        Обратный отсчёт 10…1 выводится отдельно."""
        if remaining <= 0:
            return False
        if countdown_enabled and remaining in _COUNTDOWN_WORDS:
            return False
        if remaining > 3600:
            return remaining % 1800 == 0
        if remaining > 900:
            return remaining % 900 == 0
        if remaining > 300:
            return remaining % 300 == 0
        if remaining > 60:
            return remaining % 60 == 0
        return remaining % 15 == 0

    def _format_remaining(self, seconds: int) -> str:
        """Краткий формат для озвучки: 'Осталось 5 мин 30 сек'."""
        m, s = divmod(seconds, 60)
        if s == 0:
            return f"Осталось {m} мин"
        if m == 0:
            return f"Осталось {s} сек"
        return f"Осталось {m} мин {s} сек"

    def _format_remaining_full(self, seconds: int) -> str:
        """Полный формат для TTS/Яндекс: 'Осталось 5 минут 30 секунд'."""
        m, s = divmod(seconds, 60)
        parts = []
        if m:
            parts.append(f"{m} {_pluralize(m, 'минута', 'минуты', 'минут')}")
        if s:
            parts.append(f"{s} {_pluralize(s, 'секунда', 'секунды', 'секунд')}")
        return "Осталось " + " ".join(parts) if parts else "Время вышло"

    def _format_duration_full(self, seconds: int) -> str:
        """Полный формат длительности для TTS: '5 минут 30 секунд'."""
        m, s = divmod(seconds, 60)
        parts = []
        if m:
            parts.append(f"{m} {_pluralize(m, 'минута', 'минуты', 'минут')}")
        if s:
            parts.append(f"{s} {_pluralize(s, 'секунда', 'секунды', 'секунд')}")
        return " ".join(parts) if parts else "0 секунд"

    def _is_countdown_enabled(self) -> bool:
        """Читает состояние switch.child_timer_countdown (по умолчанию включён)."""
        state = self.hass.states.get("switch.child_timer_countdown")
        return state is None or state.state == "on"

    def _current_action_type(self) -> str:
        """Конфигурируемый канал: TTS или Яндекс."""
        action_type = self.config.get(CONF_ACTION_TYPE, ACTION_TTS)
        if action_type not in (ACTION_TTS, ACTION_YANDEX):
            return ACTION_TTS
        return action_type


    async def _send_tts_only(self, message: str) -> None:
        """Отправляет только TTS/Яндекс (используется для обратного отсчёта)."""
        action_type = self._current_action_type()

        if action_type == ACTION_TTS:
            tts_entity = self.config.get(CONF_TTS_SERVICE, "")
            player = self.config.get(CONF_MEDIA_PLAYER, "")
            if tts_entity and player:
                await self.hass.services.async_call(
                    "tts", "speak",
                    {
                        "entity_id": tts_entity,
                        "media_player_entity_id": player,
                        "message": message,
                        "cache": False,
                    },
                    blocking=False,
                )

        if action_type == ACTION_YANDEX:
            yandex = self.config.get(CONF_YANDEX_STATION, "")
            if yandex:
                await self.hass.services.async_call(
                    "media_player", "play_media",
                    {
                        "entity_id": yandex,
                        "media_content_id": message,
                        "media_content_type": "text",
                    },
                    blocking=False,
                )

    async def _send_notification(self, title: str, message: str, message_tts: str | None = None) -> None:
        """Голосовое уведомление (TTS и/или Яндекс)."""
        if message_tts is None:
            message_tts = message
        action_type = self._current_action_type()

        if action_type == ACTION_TTS:
            tts_entity = self.config.get(CONF_TTS_SERVICE, "")
            player = self.config.get(CONF_MEDIA_PLAYER, "")
            if tts_entity and player:
                await self.hass.services.async_call(
                    "tts", "speak",
                    {
                        "entity_id": tts_entity,
                        "media_player_entity_id": player,
                        "message": message_tts,
                        "cache": False,
                    },
                    blocking=False,
                )

        if action_type == ACTION_YANDEX:
            yandex = self.config.get(CONF_YANDEX_STATION, "")
            if yandex:
                # Яндекс Станция: media_player.play_media с media_content_type="text"
                await self.hass.services.async_call(
                    "media_player", "play_media",
                    {
                        "entity_id": yandex,
                        "media_content_id": message_tts,
                        "media_content_type": "text",
                    },
                    blocking=False,
                )
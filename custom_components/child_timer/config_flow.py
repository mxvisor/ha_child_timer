"""Config Flow — мастер настройки Child Timer (один экземпляр)."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers import translation as translation_helper

from .const import (
    ACTION_TTS,
    ACTION_YANDEX,
    CONF_ACTION_TYPE,
    CONF_MEDIA_PLAYER,
    CONF_PRESET_MINUTES,
    CONF_TTS_SERVICE,
    CONF_YANDEX_STATION,
    DEFAULT_ACTION,
    DEFAULT_PRESETS,
    DOMAIN,
)
from .presets import sanitize_presets





def _needs_tts(action: str) -> bool:
    return action == ACTION_TTS


def _needs_yandex(action: str) -> bool:
    return action == ACTION_YANDEX


def _is_yandex_entity(hass, entity_id: str) -> bool:
    """Проверяем что entity_id принадлежит интеграции yandex_station."""
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    return entry is not None and entry.platform == "yandex_station"


def _validate_action_fields(action: str, data: dict, hass=None) -> dict:
    """Проверяем только поля, актуальные для выбранного типа оповещения."""
    errors = {}

    if _needs_tts(action):
        tts = data.get(CONF_TTS_SERVICE)
        player = data.get(CONF_MEDIA_PLAYER)
        if not tts:
            errors[CONF_TTS_SERVICE] = "required"
        elif not tts.startswith("tts."):
            errors[CONF_TTS_SERVICE] = "invalid_entity"
        if not player:
            errors[CONF_MEDIA_PLAYER] = "required"
        elif not player.startswith("media_player."):
            errors[CONF_MEDIA_PLAYER] = "invalid_entity"

    elif _needs_yandex(action):
        yandex = data.get(CONF_YANDEX_STATION)
        if not yandex:
            errors[CONF_YANDEX_STATION] = "required"
        elif not yandex.startswith("media_player."):
            errors[CONF_YANDEX_STATION] = "invalid_entity"
        elif hass is not None and not _is_yandex_entity(hass, yandex):
            # Entity существует, но не от интеграции yandex_station
            errors[CONF_YANDEX_STATION] = "not_yandex_station"

    return errors


def _optional_entity(key: str, current_value: str | None) -> vol.Optional:
    """
    Возвращает vol.Optional с default только если значение непустое.
    EntitySelector не принимает пустую строку — это и была причина ошибки
    при повторной конфигурации.
    """
    if current_value:
        return vol.Optional(key, default=current_value)
    return vol.Optional(key)


async def _build_schema(
    hass,
    current_action: str,
    current_presets: str,
    current_tts: str | None = None,
    current_player: str | None = None,
    current_yandex: str | None = None,
) -> vol.Schema:
    """Build schema with localized option labels (async)."""
    # Получаем переводы для текущего языка; делаем безопасный fallback
    tts_label = "Voice (TTS)"
    yandex_label = "Yandex Station"
    try:
        translations = await translation_helper.async_get_translations(
            hass, hass.config.language
        )
        option = translations.get("option", {})
        action_type = option.get("action_type", {})
        tts_label = action_type.get("tts", tts_label)
        yandex_label = action_type.get("yandex", yandex_label)
    except Exception:
        # В случае проблем — оставить значения по умолчанию
        pass

    return vol.Schema(
        {
            vol.Required(
                CONF_ACTION_TYPE, default=current_action
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": ACTION_TTS, "label": tts_label},
                        {"value": ACTION_YANDEX, "label": yandex_label},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(
                CONF_PRESET_MINUTES,
                default=current_presets,
            ): selector.TextSelector(),
            _optional_entity(
                CONF_TTS_SERVICE, current_tts
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="tts")
            ),
            _optional_entity(
                CONF_MEDIA_PLAYER, current_player
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="media_player")
            ),
            _optional_entity(
                CONF_YANDEX_STATION, current_yandex
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    filter=[
                        selector.EntityFilterSelectorConfig(
                            integration="yandex_station",
                            domain="media_player",
                        )
                    ]
                )
            ),
        }
    )


class ChildTimerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Мастер настройки Child Timer — допускается только один экземпляр."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors = {}
        if user_input is not None:
            user_input[CONF_PRESET_MINUTES] = sanitize_presets(
                user_input.get(CONF_PRESET_MINUTES)
            )
            errors = _validate_action_fields(
                user_input.get(CONF_ACTION_TYPE, DEFAULT_ACTION),
                user_input,
                self.hass,
            )
            if not errors:
                return self.async_create_entry(
                    title="Child Timer", data=user_input
                )

        default_presets = ", ".join(str(p) for p in DEFAULT_PRESETS)
        return self.async_show_form(
            step_id="user",
            data_schema=await _build_schema(
                self.hass, DEFAULT_ACTION, default_presets
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ChildTimerOptionsFlow(config_entry)


class ChildTimerOptionsFlow(config_entries.OptionsFlow):
    """Редактирование настроек установленной интеграции."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    @property
    def _current(self) -> dict:
        return {**self._config_entry.data, **self._config_entry.options}

    async def async_step_init(self, user_input=None):
        current = self._current
        current_action = current.get(CONF_ACTION_TYPE, DEFAULT_ACTION)
        current_presets = ", ".join(
            str(p) for p in current.get(CONF_PRESET_MINUTES, DEFAULT_PRESETS)
        )

        errors = {}
        if user_input is not None:
            user_input[CONF_PRESET_MINUTES] = sanitize_presets(
                user_input.get(CONF_PRESET_MINUTES)
            )
            errors = _validate_action_fields(
                user_input.get(CONF_ACTION_TYPE, current_action),
                user_input,
                self.hass,
            )
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=await _build_schema(
                self.hass,
                current_action=current_action,
                current_presets=current_presets,
                current_tts=current.get(CONF_TTS_SERVICE),
                current_player=current.get(CONF_MEDIA_PLAYER),
                current_yandex=current.get(CONF_YANDEX_STATION),
            ),
            errors=errors,
        )

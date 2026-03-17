"""Константы интеграции Child Timer."""

DOMAIN = "child_timer"
VERSION = "1.2.0"

# Ключи конфигурации (хранятся в config entry)
CONF_TTS_SERVICE     = "tts_service"
CONF_MEDIA_PLAYER    = "media_player"
CONF_YANDEX_STATION  = "yandex_station"
CONF_ACTION_TYPE     = "action_type"    # tts | yandex
CONF_PRESET_MINUTES  = "preset_minutes"

# Типы действий (только одиночные голосовые каналы)
ACTION_TTS    = "tts"
ACTION_YANDEX = "yandex"

# Defaults
DEFAULT_DURATION = 300    # 5 минут
DEFAULT_ACTION   = ACTION_TTS
DEFAULT_PRESETS  = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 40, 50, 60]

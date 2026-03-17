# Child Timer

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz) [![Version](https://img.shields.io/badge/version-1.4.2-blue.svg)](CHANGELOG.md)

Custom Home Assistant integration that runs a spoken timer for kids. Delivered through HACS as a single-instance integration together with its own Lovelace card.

## What you get
- Config Flow: choose voice channel - generic TTS (any `tts.*` + `media_player.*`) or Yandex Station (AlexxIT/YandexStation).
- Entities:
  - `sensor.child_timer` - state `active`/`idle`, attributes: `remaining_seconds`, `total_seconds`, `remaining_formatted`, `progress` (0..1).
  - `number.child_timer_duration` - slider 1-1440 minutes, persists across restarts, default 5 minutes.
  - `select.child_timer_preset` - preset list from the config wizard (default: 1-10, 15, 20, 25, 30, 40, 50, 60 minutes).
  - `switch.child_timer_countdown` - enables 10..1 spoken countdown near the end (on by default).
  - `button.child_timer_start` / `button.child_timer_stop` - start/stop with the current duration.
- Services: `child_timer.start` (optional `duration` in seconds, min 10) and `child_timer.stop`. The service can launch short timers down to 10 seconds even though the duration slider starts at 1 minute; this is intentional so automations can run sub-minute timers.
- Lovelace card `custom:child-timer-card` is served by the integration and tries to auto-register its resource.
- Voice notification cadence (also used for TTS/Yandex messages):
  - More than 1 hour left: every 30 minutes.
  - 60-15 minutes: every 15 minutes.
  - 15-5 minutes: every 5 minutes.
  - 5-1 minutes: every minute.
  - 60-15 seconds: every 15 seconds.
  - Optional 10..1 countdown is sent only when `switch.child_timer_countdown` is on.

## Installation (HACS custom repository)

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MXVisoR&repository=ha-child-timer&category=integration)

1. HACS -> Custom repositories -> add `https://github.com/mxvisor/ha-child-timer` with category **Integration**.
2. Install **Child Timer**, restart Home Assistant if prompted.
3. Settings -> Devices & Services -> Add Integration -> **Child Timer** -> finish the wizard.
4. The card resource is registered automatically. If auto-registration fails or
   your Lovelace resources are managed manually, go to
   **Settings → Dashboards → ⋮ → Resources → Add Resource** and enter:
   - URL: `/child_timer_static/child-timer-card.js`
   - Resource type: **JavaScript module**

## Configuration wizard
- Select the voice backend (TTS or Yandex Station). Required entities change depending on the choice.
- Provide preset minutes as a comma-separated list; they will appear in `select.child_timer_preset` and can be edited later via Options.
- Finish the wizard - all entities are created automatically; the timer uses the current `number.child_timer_duration` unless a service call provides `duration` in seconds.

![Config flow placeholder](images/config.png)

## Lovelace card
Add the card manually if it is not injected automatically:

```yaml
type: custom:child-timer-card
preset_entity: select.child_timer_preset
countdown_entity: switch.child_timer_countdown
sensor_entity: sensor.child_timer
start_entity: button.child_timer_start
stop_entity: button.child_timer_stop
title: Child Timer
```

![Widget placeholder](images/card.png)


For a quick start you can also drop `examples/ha_child_timer_card.yaml` into your dashboard.
![Widget placeholder](images/card-yaml.png)


## Quick service calls
- Start with a custom duration (seconds): `service: child_timer.start` -> `data: { duration: 900 }` (15 minutes).
- Stop early: `service: child_timer.stop`.

## Support
- Issues and questions: https://github.com/mxvisor/ha-child-timer/issues
- Changelog: [CHANGELOG.md](CHANGELOG.md)

## Credits
Built with the assistance of [Claude AI](https://www.anthropic.com) (Anthropic).
"""Утилиты для работы со списком пресетов минут."""

from __future__ import annotations

from .const import DEFAULT_PRESETS


def sanitize_presets(raw) -> list[int]:
    """Преобразует вход (str или iterable) в список уникальных минут.

    - Строка: разделение по запятым/пробелам.
    - Значения <1 или >1440 отбрасываются.
    - При ошибках возвращает DEFAULT_PRESETS.
    """
    values: list[int] = []
    seen = set()

    items = []
    if isinstance(raw, str):
        parts = raw.replace(";", ",").replace("\n", ",").split(",")
        items = [p.strip() for p in parts if p.strip()]
    elif raw is None:
        items = []
    else:
        items = list(raw)

    for item in items:
        try:
            val = int(float(item))
        except (ValueError, TypeError):
            continue
        if 1 <= val <= 1440 and val not in seen:
            seen.add(val)
            values.append(val)

    return values if values else DEFAULT_PRESETS.copy()

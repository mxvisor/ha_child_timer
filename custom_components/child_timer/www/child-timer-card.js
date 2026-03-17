/**
 * Child Timer Card — кастомная карточка для Home Assistant
 * Установка:
 *   1. Скопируйте файл в config/www/child-timer-card.js
 *   2. Настройки → Панели управления → Ресурсы → Добавить
 *      URL: /local/child-timer-card.js  |  Тип: JavaScript модуль
 *   3. Перезагрузите браузер (Ctrl+Shift+R)
 *
 * Использование в карточке (тип: custom:child-timer-card):
 *   type: custom:child-timer-card
 *   preset_entity:   select.child_timer_preset
 *   countdown_entity: switch.child_timer_countdown
 *   sensor_entity:   sensor.child_timer
 *   start_entity:    button.child_timer_start
 *   stop_entity:     button.child_timer_stop
 */

class ChildTimerCard extends HTMLElement {

  /* ── Конфигурация ───────────────────────────────────────────────────── */
  setConfig(config) {
    this._config = {
      preset_entity:    config.preset_entity    || 'select.child_timer_preset',
      countdown_entity: config.countdown_entity || 'switch.child_timer_countdown',
      sensor_entity:    config.sensor_entity    || 'sensor.child_timer',
      start_entity:     config.start_entity     || 'button.child_timer_start',
      stop_entity:      config.stop_entity      || 'button.child_timer_stop',
      title:            config.title            || 'Child Timer',
    };
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this._build();
  }

  /* ── Обновление состояния ───────────────────────────────────────────── */
  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  /* ── Первоначальная сборка DOM ──────────────────────────────────────── */
  _build() {
    this.shadowRoot.innerHTML = `
      <style>${this._css()}</style>
      <ha-card>
        <div class="card-body">

          <!-- Заголовок -->
          <div class="card-header">
            <span class="header-icon">⏱</span>
            <span class="header-title">${this._config.title}</span>
            <span class="status-badge" id="badge">...</span>
          </div>

          <!-- Дисплей времени -->
          <div class="display-wrap">
            <div class="ring-wrap">
              <svg class="ring" viewBox="0 0 120 120">
                <circle class="ring-track" cx="60" cy="60" r="52"/>
                <circle class="ring-fill"  cx="60" cy="60" r="52" id="ring-arc"/>
              </svg>
              <div class="ring-center">
                <div class="time-label" id="time-label">--:--</div>
              </div>
            </div>
          </div>

          <!-- Параметры -->
          <div class="params-section">
            <div class="param-row">
              <span class="param-label">Длительность</span>
              <div class="preset-wrap">
                <select class="param-select" id="preset-select">
                  <option>загрузка...</option>
                </select>
                <span class="preset-unit">мин</span>
              </div>
            </div>
            <div class="param-row">
              <span class="param-label">Обратный отсчёт 10…1</span>
              <label class="toggle">
                <input type="checkbox" id="countdown-toggle"/>
                <span class="toggle-track"><span class="toggle-thumb"></span></span>
              </label>
            </div>
          </div>

          <!-- Кнопки -->
          <div class="btn-row">
            <button class="btn btn-start" id="btn-start">
              <svg viewBox="0 0 24 24" class="btn-icon"><path d="M8 5v14l11-7z"/></svg>
              Старт
            </button>
            <button class="btn btn-stop" id="btn-stop">
              <svg viewBox="0 0 24 24" class="btn-icon"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
              Стоп
            </button>
          </div>

        </div>
      </ha-card>

    `;

    /* Привязка событий */
    this.shadowRoot.getElementById('preset-select').addEventListener('change', e => {
      this._callService('select', 'select_option', this._config.preset_entity, { option: e.target.value });
    });

    this.shadowRoot.getElementById('countdown-toggle').addEventListener('change', e => {
      const svc = e.target.checked ? 'turn_on' : 'turn_off';
      this._callService('switch', svc, this._config.countdown_entity);
    });

    this.shadowRoot.getElementById('btn-start').addEventListener('click', () => {
      this._callService('button', 'press', this._config.start_entity);
      this._pulse('btn-start');
    });

    this.shadowRoot.getElementById('btn-stop').addEventListener('click', () => {
      this._callService('button', 'press', this._config.stop_entity);
      this._pulse('btn-stop');
    });
  }

  /* ── Обновление UI из состояний ────────────────────────────────────── */
  _update() {
    if (!this._hass) return;

    const sensor   = this._hass.states[this._config.sensor_entity];
    const preset   = this._hass.states[this._config.preset_entity];
    const countdown = this._hass.states[this._config.countdown_entity];

    /* Дисплей таймера */
    const timeLbl  = this.shadowRoot.getElementById('time-label');
    const badge    = this.shadowRoot.getElementById('badge');
    const arc      = this.shadowRoot.getElementById('ring-arc');
    const card     = this.shadowRoot.querySelector('ha-card');

    if (!sensor) {
      timeLbl.textContent = '--:--';
      timeSub.textContent = 'интеграция не найдена';
      badge.textContent   = '?';
      badge.className = 'status-badge badge-unknown';
      return;
    }

    const state = sensor.state;
    const attrs = sensor.attributes || {};
    const formatted = attrs.remaining_formatted || '--:--';
    const progress  = attrs.progress !== undefined ? attrs.progress : 1; // 0..1

    const CIRC = 2 * Math.PI * 52;
    arc.style.strokeDasharray = CIRC;

    if (state === 'active') {
      const sec = attrs.remaining_seconds !== undefined ? attrs.remaining_seconds : 0;
      timeLbl.textContent        = this._formatSeconds(sec);
      badge.textContent          = 'активен';
      badge.className            = 'status-badge badge-active';
      arc.style.stroke           = '#06D6A0';
      arc.style.strokeDashoffset = CIRC * (1 - progress);
      card.dataset.state         = 'active';
    } else if (state === 'idle') {
      // Показываем выбранный пресет (текущую длительность)
      const presetState = this._hass.states[this._config.preset_entity];
      const presetVal   = presetState ? presetState.state : '';
      timeLbl.textContent        = this._formatPreset(presetVal);
      badge.textContent          = 'готов';
      badge.className            = 'status-badge badge-idle';
      arc.style.stroke           = 'var(--divider-color, #e0e0e0)';
      arc.style.strokeDashoffset = CIRC;
      card.dataset.state         = 'idle';
    } else {
      timeLbl.textContent        = '--:--';
      badge.textContent          = state;
      badge.className            = 'status-badge badge-unknown';
      arc.style.stroke           = '#888';
      arc.style.strokeDashoffset = CIRC;
      card.dataset.state         = '';
    }

    /* Пресет */
    if (preset) {
      const sel = this.shadowRoot.getElementById('preset-select');
      const opts = preset.attributes.options || [];
      if (sel.dataset.loaded !== JSON.stringify(opts)) {
        sel.innerHTML = opts.map(o =>
          `<option value="${o}" ${o === preset.state ? 'selected' : ''}>${o}</option>`
        ).join('');
        sel.dataset.loaded = JSON.stringify(opts);
      } else {
        sel.value = preset.state;
      }
    }

    /* Переключатель обратного отсчёта */
    if (countdown) {
      this.shadowRoot.getElementById('countdown-toggle').checked = countdown.state === 'on';
    }
  }

  /* ── Вызов сервиса ─────────────────────────────────────────────────── */
  _callService(domain, service, entityId, data = {}) {
    this._hass.callService(domain, service, { entity_id: entityId, ...data });
  }

  /* ── Анимация нажатия кнопки ───────────────────────────────────────── */
  _pulse(id) {
    const el = this.shadowRoot.getElementById(id);
    el.classList.add('pulse');
    setTimeout(() => el.classList.remove('pulse'), 400);
  }

  /* ── Форматирование секунд в MM:SS или HH:MM:SS ────────────────────── */
  _formatSeconds(totalSec) {
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    if (h > 0) {
      return String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
    }
    return String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
  }

  /* ── Форматирование пресета (число минут) в MM:SS или HH:MM:SS ──────── */
  _formatPreset(presetVal) {
    if (!presetVal) return '--:--';
    const mins = parseFloat(presetVal);
    if (isNaN(mins) || mins <= 0) return '--:--';
    return this._formatSeconds(Math.round(mins * 60));
  }

  /* ── Размер карточки (опционально) ─────────────────────────────────── */
  getCardSize() { return 4; }

  /* ── CSS ────────────────────────────────────────────────────────────── */
  _css() {
    return `
      :host { display: block; }

      ha-card {
        background: var(--ha-card-background, var(--card-background-color, #fff));
        border-radius: 16px;
        overflow: visible;
        position: relative;
      }

      .card-body {
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 20px;
      }

      /* Заголовок */
      .card-header {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .header-icon { font-size: 20px; }
      .header-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--primary-text-color);
        flex: 1;
      }
      .status-badge {
        font-size: 11px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: .05em;
      }
      .badge-active  { background: #06D6A022; color: #06D6A0; }
      .badge-idle    { background: #88888822; color: #888; }
      .badge-unknown { background: #ff990022; color: #ff9900; }

      /* Кольцо */
      .display-wrap {
        display: flex;
        justify-content: center;
      }
      .ring-wrap {
        position: relative;
        width: 140px;
        height: 140px;
      }
      .ring {
        width: 140px;
        height: 140px;
        transform: rotate(-90deg);
      }
      .ring-track {
        fill: none;
        stroke: var(--divider-color, #e0e0e0);
        stroke-width: 8;
      }
      .ring-fill {
        fill: none;
        stroke: #888;
        stroke-width: 8;
        stroke-linecap: round;
        transition: stroke-dashoffset .8s cubic-bezier(.4,0,.2,1), stroke .4s;
      }
      .ring-center {
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2px;
      }
      .time-label {
        font-size: 30px;
        font-weight: 700;
        color: var(--primary-text-color);
        font-variant-numeric: tabular-nums;
        letter-spacing: -.5px;
      }
      .time-sub {
        font-size: 11px;
        color: var(--secondary-text-color);
        text-transform: uppercase;
        letter-spacing: .06em;
      }

      /* Параметры */
      .params-section {
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding: 14px 16px;
        background: var(--secondary-background-color, #f5f5f5);
        border-radius: 12px;
      }
      .param-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }
      .param-label {
        font-size: 13px;
        color: var(--secondary-text-color);
        flex: 1;
      }
      .param-select {
        background: var(--ha-card-background, var(--card-background-color, #fff));
        color: var(--primary-text-color);
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 8px;
        padding: 5px 10px;
        font-size: 13px;
        cursor: pointer;
        min-width: 110px;
        appearance: auto;
      }
      .param-select option {
        background: var(--ha-card-background, var(--card-background-color, #fff));
        color: var(--primary-text-color);
      }
      .param-select:focus { outline: none; border-color: var(--primary-color, #03a9f4); }
      .preset-wrap { display: flex; align-items: center; gap: 6px; }
      .preset-unit { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }

      /* Переключатель */
      .toggle { cursor: pointer; }
      .toggle input { display: none; }
      .toggle-track {
        display: inline-block;
        width: 38px;
        height: 22px;
        background: var(--divider-color, #ccc);
        border-radius: 11px;
        position: relative;
        transition: background .2s;
      }
      .toggle input:checked + .toggle-track { background: var(--primary-color, #03a9f4); }
      .toggle-thumb {
        position: absolute;
        top: 2px; left: 2px;
        width: 18px; height: 18px;
        background: #fff;
        border-radius: 50%;
        box-shadow: 0 1px 3px #0003;
        transition: transform .2s;
      }
      .toggle input:checked + .toggle-track .toggle-thumb { transform: translateX(16px); }

      /* Кнопки */
      .btn-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        padding: 12px;
        border: none;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: transform .12s, opacity .12s;
      }
      .btn:active, .btn.pulse { transform: scale(.95); opacity: .85; }
      .btn-icon {
        width: 18px; height: 18px;
        fill: currentColor;
        flex-shrink: 0;
      }
      .btn-start {
        background: var(--primary-color, #03a9f4);
        color: #fff;
      }
      .btn-start:hover { opacity: .9; }
      .btn-stop {
        background: var(--secondary-background-color, #f0f0f0);
        color: var(--primary-text-color);
        border: 1px solid var(--divider-color, #e0e0e0);
      }
      .btn-stop:hover { background: #ffd6d6; border-color: #f44336; color: #f44336; }

    `;
  }
}

customElements.define('child-timer-card', ChildTimerCard);

/* Регистрация в редакторе карточек HA */
window.customCards = window.customCards || [];
window.customCards.push({
  type:        'child-timer-card',
  name:        'Child Timer',
  description: 'Карточка управления детским таймером с уведомлениями',
  preview:     false,
});
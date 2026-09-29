const KEYS = [
  ["drive_forward", "drive_forward"],
  ["drive_backward", "drive_backward"],
  ["turn_left", "drive_left"],
  ["drive_left", "drive_left"],
  ["turn_right", "drive_right"],
  ["drive_right", "drive_right"],
  ["chest_led", "chest"],
  ["backlight", "backlight"],
  ["animation", "animation"],
  ["attitude", "attitude"],
  ["battery", "battery"],
  ["volume", "volume"],
  ["image", "image"],
  ["sound", "sound"],
  ["chest", "chest"],
  ["stop", "stop"],
];

class CojiRemoteCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = undefined;
    this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    this.shadowRoot.addEventListener("change", (event) => this._onChange(event));
  }

  static getConfigElement() {
    return document.createElement("coji-remote-card-editor");
  }

  static getStubConfig(hass) {
    const deviceId = cojiDeviceIds(hass)[0];
    return deviceId ? { device_id: deviceId } : {};
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (this.shadowRoot.activeElement) {
      return;
    }
    this._render();
  }

  getCardSize() {
    return 6;
  }

  _entities() {
    const wanted = this._config.device_id;
    const found = {};
    for (const entry of cojiEntries(this._hass)) {
      if (wanted && entry.device_id && entry.device_id !== wanted) {
        continue;
      }
      const key = entryKey(entry);
      if (key && !found[key]) {
        found[key] = entry.entity_id;
      }
    }
    return found;
  }

  _state(entityId) {
    return entityId ? this._hass.states[entityId] : undefined;
  }

  _call(domain, service, data) {
    this._hass.callService(domain, service, data);
  }

  _onClick(event) {
    const button = event.target.closest("button[data-act]");
    if (!button) {
      return;
    }
    const entities = this._entities();
    const key = button.dataset.act;
    const entityId = entities[key];
    if (!entityId) {
      return;
    }
    if (key === "backlight") {
      this._call("switch", "toggle", { entity_id: entityId });
      return;
    }
    if (key === "chest") {
      this._call("light", "toggle", { entity_id: entityId });
      return;
    }
    this._call("button", "press", { entity_id: entityId });
  }

  _onChange(event) {
    const input = event.target;
    const entities = this._entities();
    if (input.dataset.select) {
      this._call("select", "select_option", {
        entity_id: entities[input.dataset.select],
        option: input.value,
      });
      return;
    }
    if (input.dataset.volume) {
      this._call("number", "set_value", {
        entity_id: entities.volume,
        value: Number(input.value),
      });
    }
  }

  _render() {
    const entities = this._entities();
    const battery = this._state(entities.battery);
    const attitude = this._state(entities.attitude);
    const backlight = this._state(entities.backlight);
    const chestState = this._state(entities.chest);
    const name = deviceName(this._hass, this._config.device_id);
    const volts = batteryText(battery);
    const pose = poseText(attitude);

    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 14px 14px 10px;
        }
        .screen {
          display: grid;
          grid-template-columns: auto 1fr;
          grid-template-areas: "icon name" "icon volts" "icon pose";
          column-gap: 12px;
          padding: 12px 14px;
          border-radius: 20px;
          background: linear-gradient(180deg, rgba(127,127,127,0.16), rgba(0,0,0,0.18));
        }
        .screen ha-icon { grid-area: icon; align-self: center; --mdc-icon-size: 36px; color: var(--state-icon-color, #90caf9); }
        .name { grid-area: name; font-weight: 700; font-size: 18px; }
        .volts { grid-area: volts; font-weight: 700; font-size: 22px; }
        .pose { grid-area: pose; opacity: 0.7; font-size: 13px; text-transform: capitalize; }
        .pad {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
          width: min(100%, 260px);
          margin: 14px auto 8px;
        }
        .pad button, .pad .gap {
          aspect-ratio: 1;
          border: none;
          border-radius: 50%;
          background: rgba(127,127,127,0.22);
          color: var(--primary-text-color);
          cursor: pointer;
          padding: 0;
        }
        .pad .gap { visibility: hidden; }
        .pad .stop { background: #c62828; color: white; }
        .pad ha-icon { --mdc-icon-size: 28px; }
        .face {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin: 8px 0;
        }
        .face button {
          border: none;
          border-radius: 16px;
          background: rgba(127,127,127,0.16);
          color: var(--primary-text-color);
          padding: 12px 8px;
          cursor: pointer;
        }
        .face button.on { background: rgba(255,193,7,0.28); }
        .face .label { display: block; font-weight: 600; }
        .face .sub { display: block; opacity: 0.7; font-size: 12px; }
        .row {
          display: grid;
          grid-template-columns: 28px 1fr;
          gap: 8px;
          align-items: center;
          margin: 8px 2px;
        }
        select, input[type="range"] { width: 100%; }
        select, .missing {
          background: transparent;
          color: var(--primary-text-color);
          border: none;
          border-bottom: 1px solid var(--divider-color, rgba(127,127,127,0.4));
          padding: 6px 0;
          font: inherit;
        }
        .missing { opacity: 0.7; padding: 8px 2px 12px; }
      </style>
      <ha-card>
        <div class="screen">
          <ha-icon icon="mdi:robot-happy"></ha-icon>
          <div class="name">${escapeHtml(name)}</div>
          <div class="volts">${escapeHtml(volts)}</div>
          <div class="pose">${escapeHtml(pose)}</div>
        </div>
        ${
          entities.drive_forward
            ? `<div class="pad">
                <span class="gap"></span>
                ${padButton("drive_forward", "mdi:chevron-up")}
                <span class="gap"></span>
                ${padButton("drive_left", "mdi:chevron-left")}
                ${padButton("stop", "mdi:stop", "stop")}
                ${padButton("drive_right", "mdi:chevron-right")}
                <span class="gap"></span>
                ${padButton("drive_backward", "mdi:chevron-down")}
                <span class="gap"></span>
              </div>
              <div class="face">
                ${faceButton("backlight", "Backlight", "mdi:television-ambient-light", backlight)}
                ${faceButton("chest", "Chest", "mdi:led-on", chestState)}
              </div>
              ${selectRow(this._state(entities.animation), "animation", "mdi:animation-play")}
              ${selectRow(this._state(entities.image), "image", "mdi:image")}
              ${selectRow(this._state(entities.sound), "sound", "mdi:music-note")}
              ${volumeRow(this._state(entities.volume))}`
            : `<p class="missing">No COJI found. Add the integration, then add this card again.</p>`
        }
      </ha-card>
    `;
  }
}

class CojiRemoteCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this.shadowRoot.addEventListener("change", (event) => {
      const deviceId = event.target.value;
      const config = { ...this._config };
      if (deviceId) {
        config.device_id = deviceId;
      } else {
        delete config.device_id;
      }
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config },
          bubbles: true,
          composed: true,
        }),
      );
    });
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass) {
      return;
    }
    const current = this._config.device_id || "";
    const options = cojiDeviceIds(this._hass)
      .map((deviceId) => {
        const name = deviceName(this._hass, deviceId);
        return `<option value="${escapeHtml(deviceId)}" ${deviceId === current ? "selected" : ""}>${escapeHtml(name)}</option>`;
      })
      .join("");
    this.shadowRoot.innerHTML = `
      <style>
        label { display: block; padding: 8px 0; font: inherit; }
        select { width: 100%; margin-top: 6px; font: inherit; }
      </style>
      <label>Robot
        <select>
          <option value="">First COJI</option>
          ${options}
        </select>
      </label>
    `;
  }
}

function cojiEntries(hass) {
  if (!hass) {
    return [];
  }
  const registry = hass.entities ? Object.values(hass.entities) : [];
  const fromRegistry = registry.filter((entry) => entry.platform === "coji");
  if (fromRegistry.length) {
    return fromRegistry;
  }
  return Object.values(hass.states || {})
    .filter((state) => state.entity_id.split(".")[1]?.includes("coji"))
    .map((state) => ({ entity_id: state.entity_id }));
}

function cojiDeviceIds(hass) {
  return [...new Set(cojiEntries(hass).map((entry) => entry.device_id).filter(Boolean))];
}

function entryKey(entry) {
  if (entry.translation_key) {
    return entry.translation_key;
  }
  const objectId = entry.entity_id.split(".")[1] || "";
  const match = KEYS.find(([suffix]) => objectId.endsWith(suffix));
  return match ? match[1] : undefined;
}

function deviceName(hass, deviceId) {
  const id = deviceId || cojiDeviceIds(hass)[0];
  const device = id && hass.devices ? hass.devices[id] : undefined;
  return device?.name_by_user || device?.name || "COJI";
}

function batteryText(state) {
  const value = Number(state?.state);
  if (!Number.isFinite(value)) {
    return "Off";
  }
  const unit = state.attributes.unit_of_measurement || "V";
  return `${value.toFixed(2)} ${unit}`;
}

function poseText(state) {
  const raw = state?.state;
  if (!raw || raw === "unknown" || raw === "unavailable" || raw === "none") {
    return "Tap an arrow";
  }
  return raw.replaceAll("_", " ");
}

function onOff(state) {
  return state?.state === "on" ? "On" : "Off";
}

function padButton(key, icon, extra = "") {
  return `<button class="${extra}" data-act="${key}" type="button"><ha-icon icon="${icon}"></ha-icon></button>`;
}

function faceButton(key, label, icon, state) {
  const on = state?.state === "on" ? "on" : "";
  return `<button class="${on}" data-act="${key}" type="button"><ha-icon icon="${icon}"></ha-icon><span class="label">${label}</span><span class="sub">${onOff(state)}</span></button>`;
}

function selectRow(state, key, icon) {
  const options = state?.attributes?.options || [];
  const current = state?.state;
  const choices = options
    .map(
      (option) =>
        `<option value="${escapeHtml(option)}" ${option === current ? "selected" : ""}>${escapeHtml(option.replaceAll("_", " "))}</option>`,
    )
    .join("");
  return `<div class="row"><ha-icon icon="${icon}"></ha-icon><select data-select="${key}">${choices}</select></div>`;
}

function volumeRow(state) {
  const value = Number(state?.state);
  const min = state?.attributes?.min ?? 0;
  const max = state?.attributes?.max ?? 100;
  const step = state?.attributes?.step ?? 1;
  const current = Number.isFinite(value) ? value : min;
  return `<div class="row"><ha-icon icon="mdi:volume-high"></ha-icon><input data-volume="1" type="range" min="${min}" max="${max}" step="${step}" value="${current}"></div>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

customElements.define("coji-remote-card", CojiRemoteCard);
customElements.define("coji-remote-card-editor", CojiRemoteCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "coji-remote-card",
  name: "COJI Remote",
  description: "Remote control for a WowWee COJI",
  preview: true,
});

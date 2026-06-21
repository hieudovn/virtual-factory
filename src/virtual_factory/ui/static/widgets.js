/* Virtual Factory — Interactive Widgets Library

   Reusable SCADA-style widgets for display and configuration:
   - TankLevelGauge: visual tank fill indicator
   - ValueBar: horizontal bar indicator (flow, pressure)
   - TrendChart: simple line chart for telemetry history
   - SliderControl: configurable slider with label
   - ToggleSwitch: on/off toggle
   - NumberSpinner: numeric input with +/- buttons
   - DataTable: sortable telemetry table
 */

const WIDGETS = (() => {

  // ==================================================================
  // TankLevelGauge — vertical tank fill indicator
  // ==================================================================

  class TankLevelGauge {
    constructor(container, opts = {}) {
      this.container = container;
      this.min = opts.min ?? 0;
      this.max = opts.max ?? 5;
      this.value = opts.value ?? 0;
      this.unit = opts.unit ?? "m";
      this.label = opts.label ?? "";
      this.warnLow = opts.warnLow ?? (this.max * 0.1);
      this.warnHigh = opts.warnHigh ?? (this.max * 0.9);
      this._build();
    }

    _build() {
      this.el = document.createElement("div");
      this.el.className = "widget tank-gauge";
      this.el.innerHTML = `
        <div class="tank-gauge-label">${this.label}</div>
        <div class="tank-gauge-body">
          <div class="tank-gauge-fill"></div>
          <div class="tank-gauge-value">--</div>
        </div>
        <div class="tank-gauge-range">
          <span>${this.max}${this.unit}</span>
          <span>${this.min}${this.unit}</span>
        </div>
      `;
      this._fillEl = this.el.querySelector(".tank-gauge-fill");
      this._valueEl = this.el.querySelector(".tank-gauge-value");
      this.container.appendChild(this.el);
      this.update(this.value);
    }

    update(value) {
      this.value = value;
      const pct = Math.max(0, Math.min(100, ((value - this.min) / (this.max - this.min)) * 100));
      this._fillEl.style.height = pct + "%";
      // Color by zone
      if (value <= this.warnLow) {
        this._fillEl.style.background = "#ef4444";
      } else if (value >= this.warnHigh) {
        this._fillEl.style.background = "#f59e0b";
      } else {
        this._fillEl.style.background = "var(--accent, #16726a)";
      }
      this._valueEl.textContent = value.toFixed(2) + " " + this.unit;
    }

    remove() {
      this.el.remove();
    }
  }

  // ==================================================================
  // ValueBar — horizontal bar indicator
  // ==================================================================

  class ValueBar {
    constructor(container, opts = {}) {
      this.container = container;
      this.min = opts.min ?? 0;
      this.max = opts.max ?? 100;
      this.value = opts.value ?? 0;
      this.unit = opts.unit ?? "";
      this.label = opts.label ?? "";
      this.color = opts.color ?? "var(--accent, #16726a)";
      this._build();
    }

    _build() {
      this.el = document.createElement("div");
      this.el.className = "widget value-bar";
      this.el.innerHTML = `
        <div class="value-bar-header">
          <span class="value-bar-label">${this.label}</span>
          <span class="value-bar-value">--</span>
        </div>
        <div class="value-bar-track">
          <div class="value-bar-fill"></div>
        </div>
        <div class="value-bar-range">
          <span>${this.min}</span>
          <span>${this.max} ${this.unit}</span>
        </div>
      `;
      this._fillEl = this.el.querySelector(".value-bar-fill");
      this._valueEl = this.el.querySelector(".value-bar-value");
      this._fillEl.style.background = this.color;
      this.container.appendChild(this.el);
      this.update(this.value);
    }

    update(value) {
      this.value = value;
      const pct = Math.max(0, Math.min(100, ((value - this.min) / (this.max - this.min)) * 100));
      this._fillEl.style.width = pct + "%";
      this._valueEl.textContent = value.toFixed(1) + " " + this.unit;
    }

    remove() {
      this.el.remove();
    }
  }

  // ==================================================================
  // TrendChart — simple line chart on Canvas
  // ==================================================================

  class TrendChart {
    constructor(container, opts = {}) {
      this.container = container;
      this.width = opts.width ?? 400;
      this.height = opts.height ?? 160;
      this.maxPoints = opts.maxPoints ?? 120;
      this.series = []; // {label, color, data: [{t, v}]}
      this._build();
    }

    _build() {
      this.el = document.createElement("div");
      this.el.className = "widget trend-chart";
      this.canvas = document.createElement("canvas");
      this.canvas.width = this.width;
      this.canvas.height = this.height;
      this.canvas.style.width = "100%";
      this.canvas.style.height = "auto";
      this.ctx = this.canvas.getContext("2d");
      this.el.appendChild(this.canvas);
      this.container.appendChild(this.el);
      this._draw();
    }

    addSeries(label, color) {
      this.series.push({ label, color, data: [] });
    }

    pushData(seriesIndex, t, v) {
      if (seriesIndex >= this.series.length) return;
      const s = this.series[seriesIndex];
      s.data.push({ t, v });
      if (s.data.length > this.maxPoints) s.data.shift();
      this._draw();
    }

    _draw() {
      const ctx = this.ctx;
      const W = this.width, H = this.height;
      const pad = { top: 12, right: 16, bottom: 24, left: 48 };
      const pw = W - pad.left - pad.right;
      const ph = H - pad.top - pad.bottom;

      ctx.clearRect(0, 0, W, H);

      // Background
      ctx.fillStyle = "#f8fafc";
      ctx.fillRect(pad.left, pad.top, pw, ph);

      // Grid lines
      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth = 0.5;
      for (let i = 0; i <= 4; i++) {
        const y = pad.top + (ph * i) / 4;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
      }

      if (!this.series.length || !this.series[0].data.length) {
        ctx.fillStyle = "#94a3b8";
        ctx.font = "11px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Waiting for data…", W / 2, H / 2);
        return;
      }

      // Compute Y range from all series
      let vMin = Infinity, vMax = -Infinity;
      for (const s of this.series) {
        for (const d of s.data) {
          if (d.v < vMin) vMin = d.v;
          if (d.v > vMax) vMax = d.v;
        }
      }
      if (vMax === vMin) { vMax = vMin + 1; vMin -= 1; }

      // Y-axis labels
      ctx.fillStyle = "#64748b";
      ctx.font = "9px Inter, sans-serif";
      ctx.textAlign = "right";
      for (let i = 0; i <= 4; i++) {
        const val = vMax - ((vMax - vMin) * i) / 4;
        const y = pad.top + (ph * i) / 4;
        ctx.fillText(val.toFixed(1), pad.left - 6, y + 3);
      }

      // Draw each series
      for (const s of this.series) {
        if (s.data.length < 2) continue;
        ctx.strokeStyle = s.color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let i = 0; i < s.data.length; i++) {
          const x = pad.left + (pw * i) / (this.maxPoints - 1);
          const y = pad.top + ph - ((s.data[i].v - vMin) / (vMax - vMin)) * ph;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
    }

    remove() {
      this.el.remove();
    }
  }

  // ==================================================================
  // SliderControl — labeled slider with number display
  // ==================================================================

  class SliderControl {
    constructor(container, opts = {}) {
      this.container = container;
      this.label = opts.label ?? "";
      this.min = opts.min ?? 0;
      this.max = opts.max ?? 100;
      this.step = opts.step ?? 1;
      this.value = opts.value ?? 50;
      this.unit = opts.unit ?? "";
      this.onChange = opts.onChange ?? (() => {});
      this._build();
    }

    _build() {
      this.el = document.createElement("div");
      this.el.className = "widget slider-control";
      this.el.innerHTML = `
        <div class="slider-header">
          <label>${this.label}</label>
          <span class="slider-value">${this.value} ${this.unit}</span>
        </div>
        <input type="range" min="${this.min}" max="${this.max}" step="${this.step}" value="${this.value}">
      `;
      this._input = this.el.querySelector("input");
      this._valueSpan = this.el.querySelector(".slider-value");
      this._input.addEventListener("input", () => {
        this.value = parseFloat(this._input.value);
        this._valueSpan.textContent = this.value + " " + this.unit;
        this.onChange(this.value);
      });
      this.container.appendChild(this.el);
    }

    setValue(v) {
      this.value = v;
      this._input.value = v;
      this._valueSpan.textContent = v + " " + this.unit;
    }

    remove() {
      this.el.remove();
    }
  }

  // ==================================================================
  // ToggleSwitch — on/off switch
  // ==================================================================

  class ToggleSwitch {
    constructor(container, opts = {}) {
      this.container = container;
      this.label = opts.label ?? "";
      this.value = opts.value ?? false;
      this.onChange = opts.onChange ?? (() => {});
      this._build();
    }

    _build() {
      this.el = document.createElement("label");
      this.el.className = "widget toggle-switch";
      this.el.innerHTML = `
        <span>${this.label}</span>
        <input type="checkbox" ${this.value ? "checked" : ""}>
        <span class="toggle-track"></span>
      `;
      this._input = this.el.querySelector("input");
      this._input.addEventListener("change", () => {
        this.value = this._input.checked;
        this.onChange(this.value);
      });
      this.container.appendChild(this.el);
    }

    remove() {
      this.el.remove();
    }
  }

  // ==================================================================
  // NumberSpinner — numeric input with increment/decrement
  // ==================================================================

  class NumberSpinner {
    constructor(container, opts = {}) {
      this.container = container;
      this.label = opts.label ?? "";
      this.min = opts.min ?? 0;
      this.max = opts.max ?? 9999;
      this.step = opts.step ?? 0.1;
      this.value = opts.value ?? 0;
      this.unit = opts.unit ?? "";
      this.decimals = opts.decimals ?? 2;
      this.onChange = opts.onChange ?? (() => {});
      this._build();
    }

    _build() {
      this.el = document.createElement("div");
      this.el.className = "widget number-spinner";
      this.el.innerHTML = `
        <label>${this.label}</label>
        <div class="spinner-row">
          <button type="button" class="spinner-dec">−</button>
          <input type="number" min="${this.min}" max="${this.max}" step="${this.step}" value="${this.value}">
          <button type="button" class="spinner-inc">+</button>
          <span class="spinner-unit">${this.unit}</span>
        </div>
      `;
      this._input = this.el.querySelector("input");
      this.el.querySelector(".spinner-dec").addEventListener("click", () => this._adjust(-this.step));
      this.el.querySelector(".spinner-inc").addEventListener("click", () => this._adjust(this.step));
      this._input.addEventListener("change", () => {
        this.value = parseFloat(this._input.value) || this.min;
        this.onChange(this.value);
      });
      this.container.appendChild(this.el);
    }

    _adjust(delta) {
      this.value = Math.max(this.min, Math.min(this.max, this.value + delta));
      this._input.value = this.value.toFixed(this.decimals);
      this.onChange(this.value);
    }

    setValue(v) {
      this.value = v;
      this._input.value = v.toFixed(this.decimals);
    }

    remove() {
      this.el.remove();
    }
  }

  // ==================================================================
  // DataTable — sortable telemetry table
  // ==================================================================

  class DataTable {
    constructor(container, opts = {}) {
      this.container = container;
      this.columns = opts.columns ?? [];
      this.maxRows = opts.maxRows ?? 50;
      this._rows = [];
      this._build();
    }

    _build() {
      this.el = document.createElement("div");
      this.el.className = "widget data-table";
      this.el.innerHTML = `
        <table>
          <thead><tr>${this.columns.map(c => `<th>${c}</th>`).join("")}</tr></thead>
          <tbody></tbody>
        </table>
      `;
      this._tbody = this.el.querySelector("tbody");
      this.container.appendChild(this.el);
    }

    addRow(cells) {
      const tr = document.createElement("tr");
      for (const cell of cells) {
        const td = document.createElement("td");
        td.textContent = cell;
        tr.appendChild(td);
      }
      this._tbody.appendChild(tr);
      this._rows.push(tr);
      while (this._rows.length > this.maxRows) {
        this._rows.shift().remove();
      }
    }

    clear() {
      this._tbody.replaceChildren();
      this._rows = [];
    }

    remove() {
      this.el.remove();
    }
  }

  // ==================================================================
  // Public API
  // ==================================================================

  return {
    TankLevelGauge,
    ValueBar,
    TrendChart,
    SliderControl,
    ToggleSwitch,
    NumberSpinner,
    DataTable,
  };
})();

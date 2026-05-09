/* RavenEye globe — playback timeline.
 *
 * Three lanes inside a 0..1000 × 0..180 viewBox:
 *
 *   y =   0..30   phase bands + labels
 *   y =  32..50   day ticks
 *   y =  52..120  event ticks (severity-scaled bars; click to scrub)
 *   y = 122..168  access-window density histogram per 15-minute bucket,
 *                 stacked: scheduled (accent) on top of dropped (muted)
 *
 * Click anywhere outside an event tick to scrub the playhead.
 */
(function (global) {
  "use strict";

  const SEV_COLOR = {
    1: "#4cc4d8",
    2: "#5fb87a",
    3: "#f0a020",
    4: "#e07b3c",
    5: "#e55a3c",
  };
  const PHASE_COLOR = {
    BLOCKADE_ACTIVE:     "#2a4a6e",
    ESCALATION:          "#a05c2a",
    CEASEFIRE_ANNOUNCED: "#2a6e4a",
    CEASEFIRE_COLLAPSE:  "#a02e2a",
    BLOCKADE_REINFORCED: "#5c3a8e",
  };
  const ALLOC_COLOR   = "#4cc4d8";
  const DROP_COLOR    = "#5a6675";
  const HIST_BUCKET_MIN = 15;     // minutes per bucket

  function svgEl(tag, attrs, parent) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) for (const k in attrs) el.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(el);
    return el;
  }

  function _buildAlloc(scenario) {
    const alloc = scenario.allocations || [];
    const byWindow = new Map();
    for (const a of alloc) {
      if (a.window_id) byWindow.set(a.window_id, a);
    }
    return byWindow;
  }

  function _bucketHistogram(scenario, allocByWindow) {
    const dur_h = scenario.meta.duration_hours;
    const dur_min = dur_h * 60;
    const n_buckets = Math.max(1, Math.ceil(dur_min / HIST_BUCKET_MIN));
    const sched = new Int32Array(n_buckets);
    const drop = new Int32Array(n_buckets);
    const t0_ms = Date.parse(scenario.meta.t0_iso);
    for (const w of (scenario.access_windows || [])) {
      const start_ms = Date.parse(w.start_iso);
      if (isNaN(start_ms)) continue;
      const min_from_t0 = (start_ms - t0_ms) / 60000;
      const idx = Math.max(0, Math.min(n_buckets - 1, Math.floor(min_from_t0 / HIST_BUCKET_MIN)));
      const a = allocByWindow.get(w.window_id);
      if (a && (a.status === "SCHEDULED" || a.status === "COLLECTED")) {
        sched[idx] += 1;
      } else {
        drop[idx] += 1;
      }
    }
    return { sched, drop, n_buckets };
  }

  function render(scenario, viewer, opts = {}) {
    const Cesium = global.Cesium;
    const svg = document.getElementById("timeline-svg");
    if (!svg) return null;
    svg.innerHTML = "";
    svg.setAttribute("viewBox", "0 0 1000 180");

    const dur_h = scenario.meta.duration_hours;
    const phases = scenario.meta.phases || [];

    // Phase bands
    for (let i = 0; i < phases.length; i++) {
      const p = phases[i];
      const next = phases[i + 1];
      const x0 = (p.start_hours / dur_h) * 1000;
      const x1 = ((next ? next.start_hours : dur_h) / dur_h) * 1000;
      const color = PHASE_COLOR[p.name] || "#444";
      svgEl("rect", { x: x0, y: 0, width: x1 - x0, height: 30, fill: color, "class": "phase-band" }, svg);
      const lbl = svgEl("text", { x: x0 + 6, y: 13, "class": "phase-label" }, svg);
      lbl.textContent = p.name.replace(/_/g, " ");
      const mult = svgEl("text", { x: x0 + 6, y: 24, "class": "phase-mult" }, svg);
      mult.textContent = "x" + (p.rate_multiplier ? p.rate_multiplier.toFixed(1) : "");
    }

    // Day ticks
    for (let h = 0; h <= dur_h; h += 24) {
      const x = (h / dur_h) * 1000;
      svgEl("line", { x1: x, y1: 32, x2: x, y2: 38, "class": "tick-day" }, svg);
      const t = svgEl("text", { x: x + 3, y: 46, "class": "tick-label" }, svg);
      t.textContent = "D" + (h / 24);
    }

    // Event ticks
    const events = scenario.events || [];
    const evLaneTop = 52, evLaneBot = 120;
    for (const ev of events) {
      const x = (ev.t_hours / dur_h) * 1000;
      const hpx = 8 + ev.severity * 12;
      const g = svgEl("g", { "data-event-id": ev.event_id }, svg);
      const line = svgEl("line", {
        x1: x, y1: evLaneBot - hpx, x2: x, y2: evLaneBot,
        stroke: SEV_COLOR[ev.severity] || "#a3b0bf",
        "class": "ev-tick" + (ev.scripted ? " scripted" : ""),
      }, g);
      const ttl = svgEl("title", {}, line);
      ttl.textContent = "t+" + ev.t_hours.toFixed(1) + "h  " + ev.event_id + "  " + ev.event_type;
      line.addEventListener("click", () => {
        if (opts.onEventClick) opts.onEventClick(ev);
      });
    }

    // Access-window density histogram lane
    const histLaneTop = 122, histLaneBot = 168;
    const allocByWindow = _buildAlloc(scenario);
    const { sched, drop, n_buckets } = _bucketHistogram(scenario, allocByWindow);
    let max_total = 1;
    for (let i = 0; i < n_buckets; i++) {
      max_total = Math.max(max_total, sched[i] + drop[i]);
    }
    const bucket_width = 1000 / n_buckets;
    const lane_h = histLaneBot - histLaneTop;
    for (let i = 0; i < n_buckets; i++) {
      const total = sched[i] + drop[i];
      if (total === 0) continue;
      const x = i * bucket_width;
      const w = Math.max(0.6, bucket_width - 0.4);
      const total_h = (total / max_total) * lane_h;
      const sched_h = (sched[i] / max_total) * lane_h;
      // dropped on bottom
      svgEl("rect", {
        x: x, y: histLaneBot - total_h, width: w, height: total_h - sched_h,
        fill: DROP_COLOR, "class": "aw-bar",
      }, svg);
      // scheduled stacked on top
      if (sched_h > 0) {
        svgEl("rect", {
          x: x, y: histLaneBot - sched_h, width: w, height: sched_h,
          fill: ALLOC_COLOR, "class": "aw-bar allocated",
        }, svg);
      }
    }
    // Lane label
    const histLabel = svgEl("text", {
      x: 6, y: histLaneTop + 9, "class": "phase-mult",
    }, svg);
    histLabel.textContent = "ACCESS WINDOWS  ·  " + HIST_BUCKET_MIN + "min  ·  ★ scheduled / · dropped";

    // Playhead group (drawn last to sit on top)
    const ph = svgEl("g", { id: "playhead-g" }, svg);
    svgEl("line", {
      id: "playhead-line",
      x1: 0, y1: 30, x2: 0, y2: histLaneBot,
      "class": "playhead",
    }, ph);
    svgEl("polygon", {
      id: "playhead-handle",
      points: "-5,30 5,30 0,38",
      "class": "playhead-handle",
    }, ph);

    svg.addEventListener("click", (e) => {
      if (e.target.tagName === "line" && e.target.classList.contains("ev-tick")) return;
      const rect = svg.getBoundingClientRect();
      const rel = (e.clientX - rect.left) / rect.width;
      const hrs = Math.max(0, Math.min(dur_h, rel * dur_h));
      const t0 = Cesium.JulianDate.fromIso8601(scenario.meta.t0_iso);
      viewer.clock.currentTime = Cesium.JulianDate.addSeconds(
        t0, hrs * 3600.0, new Cesium.JulianDate()
      );
    });

    return { svg };
  }

  function updatePlayhead(scenario, viewer) {
    const Cesium = global.Cesium;
    const dur_h = scenario.meta.duration_hours;
    const t0 = Cesium.JulianDate.fromIso8601(scenario.meta.t0_iso);
    const dt_s = Cesium.JulianDate.secondsDifference(viewer.clock.currentTime, t0);
    const t_h = Math.max(0, Math.min(dur_h, dt_s / 3600.0));
    const x = (t_h / dur_h) * 1000;
    const line = document.getElementById("playhead-line");
    const handle = document.getElementById("playhead-handle");
    if (line) { line.setAttribute("x1", x); line.setAttribute("x2", x); }
    if (handle) handle.setAttribute("transform", "translate(" + x + " 0)");

    Array.prototype.forEach.call(document.querySelectorAll(".ev-tick"), (l) => {
      const g = l.parentNode;
      const id = g.getAttribute("data-event-id");
      const ev = (scenario.events || []).find(e => e.event_id === id);
      if (ev) l.classList.toggle("future", ev.t_hours > t_h + 0.01);
    });
  }

  global.RavenEyeTimeline = { render, updatePlayhead, SEV_COLOR };
})(window);

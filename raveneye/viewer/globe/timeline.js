/* RavenEye globe — playback timeline (skeleton).
 *
 * Renders phase bands, event ticks (severity-scaled), and a playhead.
 * Click-to-scrub. Chunk 7 will add the access-window density histogram
 * and the per-bucket allocated/dropped split.
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

  function svgEl(tag, attrs, parent) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) for (const k in attrs) el.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(el);
    return el;
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
      svgEl("rect", {
        x: x0, y: 0, width: x1 - x0, height: 30,
        fill: color, "class": "phase-band",
      }, svg);
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

    // Event ticks (height by severity)
    const events = scenario.events || [];
    const laneTop = 50, laneBot = 160;
    for (const ev of events) {
      const x = (ev.t_hours / dur_h) * 1000;
      const hpx = 10 + ev.severity * 14;
      const g = svgEl("g", { "data-event-id": ev.event_id }, svg);
      const line = svgEl("line", {
        x1: x, y1: laneBot - hpx, x2: x, y2: laneBot,
        stroke: SEV_COLOR[ev.severity] || "#a3b0bf",
        "class": "ev-tick" + (ev.scripted ? " scripted" : ""),
      }, g);
      const ttl = svgEl("title", {}, line);
      ttl.textContent = "t+" + ev.t_hours.toFixed(1) + "h  " + ev.event_id + "  " + ev.event_type;
      line.addEventListener("click", () => {
        if (opts.onEventClick) opts.onEventClick(ev);
      });
    }

    // Playhead group
    const ph = svgEl("g", { id: "playhead-g" }, svg);
    svgEl("line", {
      id: "playhead-line",
      x1: 0, y1: 30, x2: 0, y2: laneBot,
      "class": "playhead",
    }, ph);
    svgEl("polygon", {
      id: "playhead-handle",
      points: "-5,30 5,30 0,38",
      "class": "playhead-handle",
    }, ph);

    // Click-to-scrub
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

    // Future tick fade
    Array.prototype.forEach.call(document.querySelectorAll(".ev-tick"), (l) => {
      const g = l.parentNode;
      const id = g.getAttribute("data-event-id");
      const ev = (scenario.events || []).find(e => e.event_id === id);
      if (ev) l.classList.toggle("future", ev.t_hours > t_h + 0.01);
    });
  }

  global.RavenEyeTimeline = { render, updatePlayhead, SEV_COLOR };
})(window);

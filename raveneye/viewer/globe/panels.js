/* RavenEye globe — side-panel rendering (constellation filter, stats,
 * selection, event feed).
 *
 * Chunk 6 ships the viewer skeleton: this file wires up the basic
 * controls. Chunk 7 will extend the selection panel with full bid +
 * allocation outcome rendering.
 */
(function (global) {
  "use strict";

  const Ground = global.RavenEyeGround;
  const Orbits = global.RavenEyeOrbits;

  function render(scenario, viewer, sat_layer, ground_layer) {
    renderStats(scenario);
    renderConstellationFilter(scenario, sat_layer);
    renderEventFeed(scenario, viewer, ground_layer.eventEntities, ground_layer.t0_iso, sat_layer);
  }

  function renderStats(scenario) {
    const m = scenario.meta || {};
    const body = document.getElementById("stats-body");
    if (!body) return;
    body.innerHTML = "";
    const rows = [
      ["events",       m.n_events],
      ["bids",         m.n_bids],
      ["satellites",   m.n_satellites],
      ["windows",      m.n_access_windows],
      ["allocations",  m.n_allocations],
      ["scheduled",    m.n_scheduled],
      ["dropped",      m.n_dropped],
      ["drop rate",    m.drop_rate != null ? (m.drop_rate * 100).toFixed(1) + "%" : "—"],
      ["welfare",      m.total_welfare],
      ["mechanism",    m.mechanism],
    ];
    for (const [k, v] of rows) {
      const a = document.createElement("div");
      a.className = "stat-label"; a.textContent = k;
      const b = document.createElement("div");
      b.className = "stat-value"; b.textContent = v == null ? "—" : String(v);
      body.appendChild(a); body.appendChild(b);
    }
  }

  function renderConstellationFilter(scenario, sat_layer) {
    const root = document.getElementById("constellation-filter");
    const countLabel = document.getElementById("constellation-count");
    if (!root) return;
    root.innerHTML = "";
    const cons = sat_layer.constellations || [];
    if (countLabel) countLabel.textContent = String(cons.length);

    for (const c of cons) {
      const row = document.createElement("label");
      row.className = "con-row";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = true;
      cb.addEventListener("change", () => {
        sat_layer.setVisible(c.constellation_id, cb.checked);
      });
      const sw = document.createElement("span");
      sw.className = "swatch";
      sw.style.background = c.color;
      const v = document.createElement("span");
      v.className = "vendor";
      v.textContent = c.vendor;
      const cnt = document.createElement("span");
      cnt.className = "count";
      cnt.textContent = c.count + (c.count === 1 ? " sat" : " sats");
      row.appendChild(cb); row.appendChild(sw); row.appendChild(v); row.appendChild(cnt);
      root.appendChild(row);
    }
  }

  function renderEventFeed(scenario, viewer, eventEntities, t0_iso, sat_layer) {
    const feed = document.getElementById("event-feed");
    const count = document.getElementById("feed-count");
    if (!feed) return;
    feed.innerHTML = "";
    const events = (scenario.events || []).slice().sort(
      (a, b) => a.t_hours - b.t_hours
    );
    if (count) count.textContent = events.length + " events";

    for (const ev of events) {
      const row = document.createElement("div");
      row.className = "feed-row" + (ev.scripted ? " scripted" : "");
      row.setAttribute("data-event-id", ev.event_id);
      row.setAttribute("data-t-hours", String(ev.t_hours));

      const t = document.createElement("div");
      t.className = "feed-t";
      t.textContent = "t+" + ev.t_hours.toFixed(1) + "h";

      const sev = document.createElement("div");
      sev.className = "feed-sev";
      sev.textContent = String(ev.severity);
      sev.style.color = Ground.SEV_COLOR[ev.severity] || "#a3b0bf";

      const text = document.createElement("div");
      text.className = "feed-text";
      const typ = document.createElement("div");
      typ.className = "feed-type";
      typ.textContent = ev.event_id + "  " + ev.event_type;
      const narr = document.createElement("div");
      narr.className = "feed-narr";
      narr.textContent = ev.narrative;
      const loc = document.createElement("div");
      loc.className = "feed-loc";
      loc.textContent = ev.location_id + "  ·  " + ev.phase;
      text.appendChild(typ); text.appendChild(narr); text.appendChild(loc);

      row.appendChild(t); row.appendChild(sev); row.appendChild(text);
      row.addEventListener("click", () => {
        selectEvent(ev, scenario, viewer, eventEntities);
      });
      feed.appendChild(row);
    }
  }

  function selectEvent(ev, scenario, viewer, eventEntities) {
    const Cesium = global.Cesium;
    const ent = eventEntities.get(ev.event_id);
    if (ent) viewer.flyTo(ent, { duration: 1.5 });

    // Highlight feed row
    Array.prototype.forEach.call(document.querySelectorAll(".feed-row"), (row) => {
      row.classList.toggle("selected", row.getAttribute("data-event-id") === ev.event_id);
    });
    // Set Cesium clock to event time
    const t0 = Cesium.JulianDate.fromIso8601(scenario.meta.t0_iso);
    viewer.clock.currentTime = Cesium.JulianDate.addSeconds(
      t0, ev.t_hours * 3600.0, new Cesium.JulianDate()
    );
    fillSelection({ kind: "event", ev: ev, scenario: scenario });
  }

  function fillSelection(payload) {
    const titleEl = document.getElementById("selection-title");
    const metaEl = document.getElementById("selection-meta");
    const body = document.getElementById("selection-body");
    if (!body) return;
    body.innerHTML = "";

    if (payload.kind === "event") {
      const ev = payload.ev;
      titleEl.textContent = "Event " + ev.event_id;
      metaEl.textContent = ev.event_type;
      addLine(body, "id", ev.event_id, true);
      addLine(body, "type", ev.event_type);
      addLine(body, "severity / confidence", ev.severity + " / " + ev.source_confidence.toFixed(2));
      addLine(body, "phase", ev.phase);
      addLine(body, "location", ev.location_id);
      addLine(body, "ltiov", ev.ltiov_hours + "h");
      const narr = document.createElement("div");
      narr.className = "sel-narr";
      narr.textContent = ev.narrative;
      body.appendChild(narr);
      const bids = (payload.scenario.bids || []).filter(b => b.event_id === ev.event_id);
      if (bids.length) {
        const head = document.createElement("div");
        head.className = "sel-line";
        head.innerHTML = "<strong>" + bids.length + " bids</strong> (sorted by priority)";
        head.style.marginTop = "10px";
        body.appendChild(head);
        bids.sort((a, b) => b.priority_score - a.priority_score).forEach((b) => {
          addLine(body, b.stakeholder_id, b.priority_score.toFixed(2));
        });
      }
    } else if (payload.kind === "satellite") {
      const sat = payload.sat;
      titleEl.textContent = "Satellite";
      metaEl.textContent = sat.constellation_id;
      addLine(body, "name", sat.name, true);
      addLine(body, "norad", String(sat.norad_id));
      addLine(body, "vendor", sat.vendor);
      addLine(body, "sensor", sat.sensor_class);
      addLine(body, "bands", (sat.spectral_bands || []).join(", "));
      addLine(body, "gsd", sat.nominal_gsd_m + " m");
      addLine(body, "swath", sat.swath_width_km + " km");
      addLine(body, "max off-nadir", sat.max_off_nadir_deg + "°");
      const aw = (payload.scenario.access_windows || [])
        .filter(w => w.sat_id === sat.sat_id);
      addLine(body, "access windows", String(aw.length));
    } else if (payload.kind === "location") {
      const loc = payload.loc;
      titleEl.textContent = "Location";
      metaEl.textContent = loc.kind;
      addLine(body, "name", loc.name, true);
      addLine(body, "country", loc.country);
      addLine(body, "lat / lon", loc.lat.toFixed(3) + ", " + loc.lon.toFixed(3));
    } else {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "Click a satellite or event marker to inspect.";
      body.appendChild(empty);
    }
  }

  function addLine(body, label, value, isId) {
    const row = document.createElement("div");
    row.className = isId ? "sel-id" : "sel-line";
    if (isId) {
      row.textContent = value;
    } else {
      const k = document.createElement("span");
      k.style.color = "var(--muted)";
      k.style.marginRight = "8px";
      k.textContent = label;
      const v = document.createElement("strong");
      v.textContent = " " + value;
      row.appendChild(k);
      row.appendChild(v);
    }
    body.appendChild(row);
  }

  global.RavenEyePanels = { render, fillSelection, selectEvent };
})(window);

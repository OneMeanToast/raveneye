/* RavenEye globe — side-panel rendering.
 *
 * Stats grid, constellation filter, scrollable event feed, and the
 * selection inspector for sats / events / locations / bids. The
 * selection panel is the bid-to-collection tether: clicking an event
 * shows each derived bid alongside the allocation outcome (which sat,
 * which window, what status, welfare contribution).
 */
(function (global) {
  "use strict";

  const Ground = global.RavenEyeGround;

  // Singleton state populated by render(); used by the selection helpers.
  const ctx = {
    scenario: null,
    viewer: null,
    satLayer: null,
    eventEntities: null,
    locationEntities: null,
    coverageLayer: null,
    bidsByEvent: null,
    allocationByBidId: null,
    allocationByWindowId: null,
    windowsById: null,
    satsById: null,
    stakeholdersById: null,
  };

  function _index(scenario) {
    const bidsByEvent = new Map();
    for (const b of (scenario.bids || [])) {
      let arr = bidsByEvent.get(b.event_id);
      if (!arr) { arr = []; bidsByEvent.set(b.event_id, arr); }
      arr.push(b);
    }
    for (const arr of bidsByEvent.values()) {
      arr.sort((a, b) => b.priority_score - a.priority_score);
    }
    const stakeholdersById = new Map();
    for (const s of (scenario.stakeholders || [])) {
      stakeholdersById.set(s.stakeholder_id, s);
    }
    const windowsById = new Map();
    for (const w of (scenario.access_windows || [])) {
      windowsById.set(w.window_id, w);
    }
    const satsById = new Map();
    for (const s of (scenario.satellites || [])) {
      satsById.set(s.sat_id, s);
    }
    return { bidsByEvent, stakeholdersById, windowsById, satsById };
  }

  function render(scenario, viewer, satLayer, ground_layer, coverageLayer) {
    const idx = _index(scenario);
    ctx.scenario = scenario;
    ctx.viewer = viewer;
    ctx.satLayer = satLayer;
    ctx.eventEntities = ground_layer.eventEntities;
    ctx.locationEntities = ground_layer.locationEntities;
    ctx.coverageLayer = coverageLayer;
    ctx.bidsByEvent = idx.bidsByEvent;
    ctx.stakeholdersById = idx.stakeholdersById;
    ctx.windowsById = idx.windowsById;
    ctx.satsById = idx.satsById;
    ctx.allocationByBidId = (coverageLayer && coverageLayer.allocationByBidId) || new Map();
    ctx.allocationByWindowId = (coverageLayer && coverageLayer.allocationByWindowId) || new Map();

    renderStats(scenario);
    renderConstellationFilter(scenario, satLayer);
    renderEventFeed(scenario, viewer);
  }

  function _pct(x) {
    return (x != null) ? (x * 100).toFixed(1) + "%" : "—";
  }

  function renderStats(scenario) {
    const m = scenario.meta || {};
    const body = document.getElementById("stats-body");
    if (!body) return;
    body.innerHTML = "";
    const rows = [
      ["events",         m.n_events],
      ["bids",           m.n_bids],
      ["satellites",     m.n_satellites],
      ["windows",        m.n_access_windows],
      ["allocations",    m.n_allocations],
      ["scheduled",      m.n_scheduled],
      ["dropped",        m.n_dropped],
      ["drop rate",      _pct(m.drop_rate)],
      ["welfare",        m.total_welfare],
      ["mechanism",      m.mechanism],
      // Delivery-pipeline aggregates (Chunk 2)
      ["delivered",      m.n_delivered],
      ["proc. failed",   m.n_processing_failed],
      ["deadline miss",  m.n_deadline_missed],
      ["delivery rate",  _pct(m.delivery_rate)],
      ["proc. success",  _pct(m.processing_success_rate)],
    ];
    for (const [k, v] of rows) {
      const a = document.createElement("div");
      a.className = "stat-label"; a.textContent = k;
      const b = document.createElement("div");
      b.className = "stat-value"; b.textContent = v == null ? "—" : String(v);
      body.appendChild(a); body.appendChild(b);
    }
  }

  function renderConstellationFilter(scenario, satLayer) {
    const root = document.getElementById("constellation-filter");
    const countLabel = document.getElementById("constellation-count");
    if (!root) return;
    root.innerHTML = "";
    const cons = satLayer.constellations || [];
    if (countLabel) countLabel.textContent = String(cons.length);
    for (const c of cons) {
      const row = document.createElement("label");
      row.className = "con-row";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = true;
      cb.addEventListener("change", () => satLayer.setVisible(c.constellation_id, cb.checked));
      const sw = document.createElement("span");
      sw.className = "swatch"; sw.style.background = c.color;
      const v = document.createElement("span");
      v.className = "vendor"; v.textContent = c.vendor;
      const cnt = document.createElement("span");
      cnt.className = "count";
      cnt.textContent = c.count + (c.count === 1 ? " sat" : " sats");
      row.appendChild(cb); row.appendChild(sw); row.appendChild(v); row.appendChild(cnt);
      root.appendChild(row);
    }
  }

  function renderEventFeed(scenario, viewer) {
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
      t.className = "feed-t"; t.textContent = "t+" + ev.t_hours.toFixed(1) + "h";
      const sev = document.createElement("div");
      sev.className = "feed-sev"; sev.textContent = String(ev.severity);
      sev.style.color = Ground.SEV_COLOR[ev.severity] || "#a3b0bf";
      const text = document.createElement("div");
      text.className = "feed-text";
      const typ = document.createElement("div");
      typ.className = "feed-type";
      typ.textContent = ev.event_id + "  " + ev.event_type;
      const narr = document.createElement("div");
      narr.className = "feed-narr"; narr.textContent = ev.narrative;
      const loc = document.createElement("div");
      loc.className = "feed-loc";
      loc.textContent = ev.location_id + "  ·  " + ev.phase;
      text.appendChild(typ); text.appendChild(narr); text.appendChild(loc);
      row.appendChild(t); row.appendChild(sev); row.appendChild(text);
      row.addEventListener("click", () => selectEvent(ev));
      feed.appendChild(row);
    }
  }

  function selectEvent(ev) {
    const Cesium = global.Cesium;
    const ent = ctx.eventEntities && ctx.eventEntities.get(ev.event_id);
    if (ent) ctx.viewer.flyTo(ent, { duration: 1.5 });
    Array.prototype.forEach.call(document.querySelectorAll(".feed-row"), (row) => {
      row.classList.toggle("selected", row.getAttribute("data-event-id") === ev.event_id);
    });
    const t0 = Cesium.JulianDate.fromIso8601(ctx.scenario.meta.t0_iso);
    ctx.viewer.clock.currentTime = Cesium.JulianDate.addSeconds(
      t0, ev.t_hours * 3600.0, new Cesium.JulianDate()
    );
    fillEventSelection(ev);
  }

  function fillEventSelection(ev) {
    const titleEl = document.getElementById("selection-title");
    const metaEl = document.getElementById("selection-meta");
    const body = document.getElementById("selection-body");
    if (!body) return;
    body.innerHTML = "";
    titleEl.textContent = "Event " + ev.event_id;
    metaEl.textContent = ev.event_type;

    addLine(body, "id", ev.event_id, /*isId=*/true);
    addLine(body, "type", ev.event_type);
    addLine(body, "severity / confidence", ev.severity + " / " + ev.source_confidence.toFixed(2));
    addLine(body, "ltiov", ev.ltiov_hours + "h");
    addLine(body, "location", ev.location_id);
    addLine(body, "phase", ev.phase);
    const narr = document.createElement("div");
    narr.className = "sel-narr"; narr.textContent = ev.narrative;
    body.appendChild(narr);

    const bids = ctx.bidsByEvent.get(ev.event_id) || [];
    if (bids.length) {
      const head = document.createElement("div");
      head.className = "sel-line";
      head.style.marginTop = "12px";
      head.innerHTML = "<strong>" + bids.length + " bids</strong> &nbsp; (priority × allocation)";
      body.appendChild(head);
      for (const b of bids) {
        body.appendChild(_renderBidCard(b));
      }
    }
  }

  function _renderBidCard(bid) {
    const wrap = document.createElement("div");
    wrap.className = "bid-card";
    wrap.style.marginTop = "8px";
    wrap.style.padding = "8px 10px";
    wrap.style.border = "1px solid var(--border)";
    wrap.style.background = "var(--panel-2)";

    const head = document.createElement("div");
    head.style.display = "flex";
    head.style.justifyContent = "space-between";
    head.style.alignItems = "baseline";
    head.style.gap = "12px";

    const stake = document.createElement("div");
    stake.style.fontFamily = "var(--mono)";
    stake.style.fontSize = "11px";
    stake.style.letterSpacing = "0.06em";
    stake.style.textTransform = "uppercase";
    stake.style.color = "var(--text)";
    const sh = ctx.stakeholdersById.get(bid.stakeholder_id);
    stake.textContent = sh ? sh.display_name : bid.stakeholder_id;

    const score = document.createElement("div");
    score.style.fontFamily = "var(--mono)";
    score.style.fontSize = "13px";
    score.style.fontWeight = "600";
    score.style.color = "var(--amber)";
    score.textContent = bid.priority_score.toFixed(2);
    head.appendChild(stake); head.appendChild(score);
    wrap.appendChild(head);

    const rationale = document.createElement("div");
    rationale.style.fontSize = "11.5px";
    rationale.style.color = "var(--text-dim)";
    rationale.style.lineHeight = "1.45";
    rationale.style.marginTop = "4px";
    rationale.textContent = bid.rationale;
    wrap.appendChild(rationale);

    // Allocation outcome — the v0.2 bid-to-collection tether.
    const alloc = ctx.allocationByBidId.get(bid.bid_id);
    const outcome = document.createElement("div");
    outcome.style.marginTop = "6px";
    outcome.style.padding = "6px 8px";
    outcome.style.borderTop = "1px dashed var(--border)";
    outcome.style.fontFamily = "var(--mono)";
    outcome.style.fontSize = "10.5px";
    outcome.style.letterSpacing = "0.04em";
    if (!alloc) {
      outcome.style.color = "var(--muted)";
      outcome.textContent = "no allocation";
    } else if (alloc.status === "SCHEDULED" || alloc.status === "COLLECTED") {
      const w = ctx.windowsById.get(alloc.window_id);
      outcome.style.color = "var(--text)";
      const link = document.createElement("a");
      link.href = "#";
      link.style.color = "var(--accent)";
      link.style.textDecoration = "none";
      link.textContent = alloc.sat_id || "(unknown sat)";
      link.addEventListener("click", (e) => {
        e.preventDefault();
        focusAllocation(alloc, w);
      });

      // Lifecycle (chunk 2): final status + processing/delivery latency.
      const lc = alloc.lifecycle || {};
      const final = lc.final_status || alloc.status;
      const FINAL_COLOR = {
        DELIVERED:         "var(--green)",
        DEADLINE_MISSED:   "var(--amber)",
        PROCESSING_FAILED: "var(--red)",
        DROPPED:           "var(--muted)",
      };
      const statusBadge = document.createElement("span");
      statusBadge.textContent = "  " + final;
      statusBadge.style.color = FINAL_COLOR[final] || "var(--text)";
      statusBadge.style.fontWeight = "600";

      const win = document.createElement("div");
      win.style.color = "var(--text-dim)";
      win.style.marginTop = "2px";
      if (w) {
        const dt = w.duration_s != null ? w.duration_s.toFixed(0) + "s" : "";
        win.textContent = w.window_id + "  " + (w.start_iso || "")
          .substring(11, 16) + "Z  " + dt
          + "  q=" + (w.quality_score != null ? w.quality_score : "—");
      } else {
        win.textContent = alloc.window_id;
      }

      // Delivery line: collected → processed → delivered with per-vendor latencies.
      const delivery = document.createElement("div");
      delivery.style.color = "var(--text-dim)";
      delivery.style.marginTop = "2px";
      if (lc.collected_iso) {
        const collected = lc.collected_iso.substring(11, 16) + "Z";
        const processed = lc.processing_complete_iso
          ? lc.processing_complete_iso.substring(11, 16) + "Z" : "—";
        const delivered = lc.delivered_iso
          ? lc.delivered_iso.substring(11, 16) + "Z" : "—";
        const latPP = lc.processing_latency_min != null
          ? "+" + Math.round(lc.processing_latency_min) + "m" : "";
        const latDD = lc.delivery_latency_min != null
          ? "+" + Math.round(lc.delivery_latency_min) + "m" : "";
        delivery.textContent =
          "captured " + collected + " → processed " + processed + " " + latPP
          + " → delivered " + delivered + " " + latDD;
      } else {
        delivery.textContent = "lifecycle: no data";
      }

      const welfare = document.createElement("div");
      welfare.style.color = "var(--text-dim)";
      welfare.textContent = "welfare " + (alloc.welfare != null ? alloc.welfare : "—")
        + "  ·  " + alloc.mechanism;

      outcome.appendChild(link); outcome.appendChild(statusBadge);
      outcome.appendChild(win); outcome.appendChild(delivery); outcome.appendChild(welfare);
    } else {
      outcome.style.color = "var(--red)";
      outcome.textContent = "DROPPED  ·  " + alloc.mechanism + "  ·  " + (alloc.notes || "");
    }
    wrap.appendChild(outcome);
    return wrap;
  }

  /** Snap clock to window start, fly to satellite, follow it. */
  function focusAllocation(alloc, win) {
    if (!ctx.viewer || !alloc) return;
    const Cesium = global.Cesium;
    if (win && win.start_iso) {
      ctx.viewer.clock.currentTime = Cesium.JulianDate.fromIso8601(win.start_iso);
    }
    if (alloc.sat_id) {
      ctx.satLayer.follow(alloc.sat_id);
      window.RavenEyeState.selectedSatId = alloc.sat_id;
      const sat = ctx.satsById.get(alloc.sat_id);
      if (sat) fillSatSelection(sat);
    }
  }

  function fillSatSelection(sat) {
    const titleEl = document.getElementById("selection-title");
    const metaEl = document.getElementById("selection-meta");
    const body = document.getElementById("selection-body");
    if (!body) return;
    body.innerHTML = "";
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

    const aw = (ctx.scenario.access_windows || []).filter(w => w.sat_id === sat.sat_id);
    aw.sort((a, b) => (a.start_iso || "").localeCompare(b.start_iso || ""));
    const head = document.createElement("div");
    head.className = "sel-line";
    head.style.marginTop = "10px";
    const scheduled = aw.filter(w => ctx.allocationByWindowId.has(w.window_id));
    head.innerHTML = "<strong>" + aw.length + " access windows</strong> &nbsp; ("
      + scheduled.length + " scheduled)";
    body.appendChild(head);

    const wrap = document.createElement("div");
    wrap.style.marginTop = "4px";
    wrap.style.maxHeight = "220px";
    wrap.style.overflowY = "auto";
    wrap.style.fontFamily = "var(--mono)";
    wrap.style.fontSize = "10.5px";
    for (const w of aw) {
      const row = document.createElement("div");
      row.style.padding = "3px 0";
      row.style.borderBottom = "1px dashed var(--border)";
      const alloc = ctx.allocationByWindowId.get(w.window_id);
      const isAlloc = !!alloc;
      const color = isAlloc ? "var(--accent)" : "var(--muted)";
      const time = (w.start_iso || "").substring(5, 16).replace("T", " ");
      const tgt = w.target_id || (w.target_lat.toFixed(2) + "," + w.target_lon.toFixed(2));
      row.innerHTML = '<span style="color:' + color + '">'
        + time + '</span>  ' + tgt
        + '  q=' + (w.quality_score != null ? w.quality_score : "—")
        + (isAlloc ? '  <span style="color:var(--green)">★</span>' : "");
      if (isAlloc) {
        row.style.cursor = "pointer";
        row.addEventListener("click", () => focusAllocation(alloc, w));
      }
      wrap.appendChild(row);
    }
    body.appendChild(wrap);
  }

  function fillSelection(payload) {
    if (payload.kind === "event") {
      // Re-run the full event flow so we sync the camera/clock too.
      ctx.scenario = payload.scenario;
      selectEvent(payload.ev);
    } else if (payload.kind === "satellite") {
      fillSatSelection(payload.sat);
    } else if (payload.kind === "location") {
      const titleEl = document.getElementById("selection-title");
      const metaEl = document.getElementById("selection-meta");
      const body = document.getElementById("selection-body");
      body.innerHTML = "";
      titleEl.textContent = "Location";
      metaEl.textContent = payload.loc.kind;
      addLine(body, "name", payload.loc.name, true);
      addLine(body, "country", payload.loc.country);
      addLine(body, "lat / lon",
        payload.loc.lat.toFixed(3) + ", " + payload.loc.lon.toFixed(3));
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

  global.RavenEyePanels = {
    render,
    fillSelection,
    selectEvent: (ev /*, ...legacy args ignored */) => selectEvent(ev),
  };
})(window);

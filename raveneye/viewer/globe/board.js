/* RavenEye globe — Gantt + Kanban delivery view (chunk 4 of v0.2.x).
 *
 * Two coordinated views on the same allocation set:
 *
 *   GANTT:   one row per target location; each scheduled allocation
 *            renders as a horizontal bar spanning collection →
 *            processing → in-transit → delivered, color-coded by
 *            lifecycle stage. Bar height scales with bid priority so
 *            high-priority work reads at a glance. Vertical playhead
 *            tracks the viewer clock.
 *
 *   KANBAN:  five-column board grouping allocations by their CURRENT
 *            lifecycle stage at the playback clock:
 *              BIDDED → COLLECTING → PROCESSING → IN_TRANSIT → DELIVERED
 *            Cards flow column-to-column as the clock advances. Plus
 *            a sticky FAILURES panel showing terminal DEADLINE_MISSED
 *            and PROCESSING_FAILED rows.
 *
 * Reads scenario.allocations (with optional `lifecycle` sub-dict from the
 * delivery pipeline). Falls back gracefully if lifecycle is absent —
 * everything just renders as SCHEDULED/DROPPED.
 */
(function (global) {
  "use strict";

  const STAGE_COLOR = {
    PENDING:           "#5a6675",
    COLLECTING:        "#4cc4d8",
    PROCESSING:        "#f0a020",
    IN_TRANSIT:        "#e07b3c",
    DELIVERED:         "#5fb87a",
    DEADLINE_MISSED:   "#a07242",
    PROCESSING_FAILED: "#e55a3c",
    DROPPED:           "#3a4856",
  };
  const STAGE_LABEL = {
    BIDDED:            "BIDDED",
    COLLECTING:        "COLLECTING",
    PROCESSING:        "PROCESSING",
    IN_TRANSIT:        "IN TRANSIT",
    DELIVERED:         "DELIVERED",
    DEADLINE_MISSED:   "DEADLINE MISSED",
    PROCESSING_FAILED: "PROC. FAILED",
  };

  // ---------- helpers ----------

  function svgEl(tag, attrs, parent) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) for (const k in attrs) el.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(el);
    return el;
  }

  function _parseIsoMs(iso) {
    if (!iso) return null;
    const ms = Date.parse(iso);
    return isNaN(ms) ? null : ms;
  }

  function _alloc_t_range(alloc, win) {
    /* Returns [start_ms, end_ms] for the gantt bar. start = window.start;
       end = delivered_iso when known, else window.end. */
    if (!win) return null;
    const start = _parseIsoMs(win.start_iso);
    if (start == null) return null;
    const lc = alloc.lifecycle || {};
    const end = _parseIsoMs(lc.delivered_iso) || _parseIsoMs(win.end_iso) || (start + 60000);
    return [start, end];
  }

  function _stageAt(alloc, win, t_ms) {
    /* Returns one of BIDDED, COLLECTING, PROCESSING, IN_TRANSIT, or a
       terminal stage name. Mirrors raveneye.delivery.lifecycle_state_at
       on the Python side. */
    if (alloc.status === "DROPPED") return "DROPPED";
    if (!win) return alloc.status || "BIDDED";
    const start = _parseIsoMs(win.start_iso);
    const end = _parseIsoMs(win.end_iso);
    const lc = alloc.lifecycle || {};
    const final = lc.final_status || alloc.status;

    if (start != null && t_ms < start) return "BIDDED";
    if (end != null && t_ms < end) return "COLLECTING";
    const proc_done = _parseIsoMs(lc.processing_complete_iso);
    if (proc_done != null && t_ms < proc_done) return "PROCESSING";
    const delivered = _parseIsoMs(lc.delivered_iso);
    if (delivered != null && t_ms < delivered) return "IN_TRANSIT";
    return final || "DELIVERED";
  }

  function _t_h_to_ms(scenario, t_h) {
    return Date.parse(scenario.meta.t0_iso) + t_h * 3600 * 1000;
  }

  function _viewer_t_ms(scenario, viewer) {
    const Cesium = global.Cesium;
    const t0 = Cesium.JulianDate.fromIso8601(scenario.meta.t0_iso);
    const dt_s = Cesium.JulianDate.secondsDifference(viewer.clock.currentTime, t0);
    return Date.parse(scenario.meta.t0_iso) + dt_s * 1000;
  }

  function _maxPriority(allocations) {
    let max = 1.0;
    for (const a of allocations) {
      if (a.priority_score > max) max = a.priority_score;
    }
    return max;
  }

  // ---------- Gantt ----------

  function renderGantt(scenario) {
    const svg = document.getElementById("gantt-svg");
    if (!svg) return null;
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    const dur_h = scenario.meta.duration_hours;
    const t0_ms = Date.parse(scenario.meta.t0_iso);
    const dur_ms = dur_h * 3600 * 1000;

    // Group allocations by target_id
    const allocs = scenario.allocations || [];
    const winsById = new Map();
    for (const w of (scenario.access_windows || [])) winsById.set(w.window_id, w);
    const byTarget = new Map();
    for (const a of allocs) {
      if (a.status !== "SCHEDULED") continue;
      const w = winsById.get(a.window_id);
      if (!w) continue;
      const tgt = w.target_id || (w.target_lat.toFixed(2) + "," + w.target_lon.toFixed(2));
      let arr = byTarget.get(tgt);
      if (!arr) { arr = []; byTarget.set(tgt, arr); }
      arr.push({ alloc: a, win: w });
    }

    // Sort targets by allocation count desc — busiest at top
    const targets = Array.from(byTarget.keys())
      .sort((a, b) => byTarget.get(b).length - byTarget.get(a).length);

    const ROW_H = 26;
    const HEADER_H = 30;
    const LEFT_PAD = 180;
    const RIGHT_PAD = 12;
    const W = 1600; // virtual viewBox width
    const usableW = W - LEFT_PAD - RIGHT_PAD;
    const totalH = HEADER_H + targets.length * ROW_H + 12;
    svg.setAttribute("viewBox", `0 0 ${W} ${totalH}`);
    svg.setAttribute("height", String(totalH));
    svg.style.minHeight = totalH + "px";

    // Header: day ticks
    for (let h = 0; h <= dur_h; h += 24) {
      const x = LEFT_PAD + (h / dur_h) * usableW;
      svgEl("line", {
        x1: x, y1: 18, x2: x, y2: totalH,
        stroke: "#1a232c", "stroke-width": 1,
      }, svg);
      const t = svgEl("text", {
        x: x + 3, y: 14, "class": "gantt-tick",
      }, svg);
      t.textContent = "D" + (h / 24);
    }

    const maxPrio = _maxPriority(allocs);

    // Rows
    targets.forEach((tgt, i) => {
      const y = HEADER_H + i * ROW_H;
      // Row striping
      if (i % 2 === 0) {
        svgEl("rect", {
          x: 0, y: y, width: W, height: ROW_H,
          fill: "#0a0f15",
        }, svg);
      }
      // Target label
      const lbl = svgEl("text", {
        x: 8, y: y + ROW_H * 0.65,
        "class": "gantt-target",
      }, svg);
      lbl.textContent = tgt;
      const cnt = svgEl("text", {
        x: LEFT_PAD - 8, y: y + ROW_H * 0.65,
        "class": "gantt-target-count",
        "text-anchor": "end",
      }, svg);
      cnt.textContent = byTarget.get(tgt).length;

      // Bars for this target
      for (const { alloc, win } of byTarget.get(tgt)) {
        const range = _alloc_t_range(alloc, win);
        if (!range) continue;
        const [start_ms, end_ms] = range;
        const x0 = LEFT_PAD + ((start_ms - t0_ms) / dur_ms) * usableW;
        const x1 = LEFT_PAD + Math.min(1, (end_ms - t0_ms) / dur_ms) * usableW;
        const barW = Math.max(1.5, x1 - x0);
        const prioFrac = Math.max(0.25, alloc.priority_score / maxPrio);
        const barH = 6 + prioFrac * (ROW_H - 12);
        const barY = y + (ROW_H - barH) / 2;

        // Sub-segments by lifecycle stage
        const win_end_ms = _parseIsoMs(win.end_iso);
        const lc = alloc.lifecycle || {};
        const proc_ms = _parseIsoMs(lc.processing_complete_iso);
        const delivered_ms = _parseIsoMs(lc.delivered_iso);
        const final = lc.final_status || alloc.status;

        function _xAt(ms) {
          return LEFT_PAD + Math.max(0, Math.min(1, (ms - t0_ms) / dur_ms)) * usableW;
        }

        // 1. Collecting [start, end]
        if (win_end_ms != null) {
          const cx0 = _xAt(start_ms);
          const cx1 = _xAt(win_end_ms);
          if (cx1 > cx0) {
            svgEl("rect", {
              x: cx0, y: barY, width: Math.max(1, cx1 - cx0), height: barH,
              fill: STAGE_COLOR.COLLECTING, opacity: 0.92,
            }, svg);
          }
        }
        // 2. Processing [end, processing_complete]
        if (win_end_ms != null && proc_ms != null) {
          const px0 = _xAt(win_end_ms);
          const px1 = _xAt(proc_ms);
          if (px1 > px0) {
            svgEl("rect", {
              x: px0, y: barY + barH * 0.25, width: Math.max(1, px1 - px0),
              height: barH * 0.5,
              fill: STAGE_COLOR.PROCESSING, opacity: 0.85,
            }, svg);
          }
        }
        // 3. In-transit [processing_complete, delivered]
        if (proc_ms != null && delivered_ms != null) {
          const ix0 = _xAt(proc_ms);
          const ix1 = _xAt(delivered_ms);
          if (ix1 > ix0) {
            svgEl("rect", {
              x: ix0, y: barY + barH * 0.3, width: Math.max(1, ix1 - ix0),
              height: barH * 0.4,
              fill: STAGE_COLOR.IN_TRANSIT, opacity: 0.9,
            }, svg);
          }
        }
        // 4. Terminal marker at the end of the bar
        if (delivered_ms != null) {
          const tx = _xAt(delivered_ms);
          svgEl("circle", {
            cx: tx, cy: barY + barH / 2, r: Math.max(2, barH * 0.45),
            fill: STAGE_COLOR[final] || STAGE_COLOR.DELIVERED,
          }, svg);
        } else if (win_end_ms != null) {
          const tx = _xAt(win_end_ms);
          svgEl("circle", {
            cx: tx, cy: barY + barH / 2, r: 2.5,
            fill: STAGE_COLOR[final] || STAGE_COLOR.DELIVERED, opacity: 0.7,
          }, svg);
        }

        // Tooltip
        const title = svgEl("title", {}, svg);
        title.textContent =
          alloc.bid_id + " · sat " + (alloc.sat_id || "—") +
          " · priority " + alloc.priority_score +
          " · " + (final || "SCHEDULED") +
          (lc.delivered_iso ? "\ndelivered " + lc.delivered_iso : "");
      }
    });

    // Empty-state
    if (targets.length === 0) {
      const t = svgEl("text", {
        x: W / 2, y: HEADER_H + 40,
        "text-anchor": "middle",
        fill: "#5a6675",
        "font-size": "14",
      }, svg);
      t.textContent = "No scheduled allocations to chart.";
    }

    return { totalH };
  }

  function updateGanttPlayhead(scenario, viewer) {
    const svg = document.getElementById("gantt-svg");
    if (!svg) return;
    let ph = document.getElementById("gantt-playhead");
    const dur_h = scenario.meta.duration_hours;
    const t0_ms = Date.parse(scenario.meta.t0_iso);
    const dur_ms = dur_h * 3600 * 1000;
    const t_ms = _viewer_t_ms(scenario, viewer);
    const W = 1600, LEFT_PAD = 180, RIGHT_PAD = 12;
    const usableW = W - LEFT_PAD - RIGHT_PAD;
    const x = LEFT_PAD + Math.max(0, Math.min(1, (t_ms - t0_ms) / dur_ms)) * usableW;

    if (!ph) {
      ph = svgEl("line", {
        id: "gantt-playhead",
        x1: x, x2: x, y1: 0, y2: 4000,
        stroke: "#4cc4d8", "stroke-width": 1.5,
        opacity: 0.85,
      }, svg);
    } else {
      ph.setAttribute("x1", x);
      ph.setAttribute("x2", x);
    }
  }

  // ---------- Kanban ----------

  const KANBAN_COLUMNS = [
    "BIDDED", "COLLECTING", "PROCESSING", "IN_TRANSIT", "DELIVERED",
  ];
  const FAILURE_COLUMNS = ["DEADLINE_MISSED", "PROCESSING_FAILED", "DROPPED"];

  function _buildKanbanCard(alloc, win, target_id, sat) {
    const card = document.createElement("div");
    card.className = "kb-card";
    card.title = alloc.bid_id + " — " + (alloc.notes || "");

    const head = document.createElement("div");
    head.className = "kb-card-head";
    const id = document.createElement("span");
    id.className = "kb-id";
    id.textContent = alloc.bid_id;
    const prio = document.createElement("span");
    prio.className = "kb-prio";
    prio.textContent = alloc.priority_score != null
      ? alloc.priority_score.toFixed(2) : "—";
    head.appendChild(id); head.appendChild(prio);
    card.appendChild(head);

    const target = document.createElement("div");
    target.className = "kb-target";
    target.textContent = target_id || "—";
    card.appendChild(target);

    const sub = document.createElement("div");
    sub.className = "kb-sub";
    const satId = alloc.sat_id || "no sat";
    const winTime = win && win.start_iso ? win.start_iso.substring(11, 16) + "Z" : "—";
    sub.textContent = satId + "  ·  " + winTime;
    card.appendChild(sub);

    return card;
  }

  function renderKanban(scenario, viewer) {
    const root = document.getElementById("kanban-body");
    if (!root) return;
    root.innerHTML = "";

    const t_ms = _viewer_t_ms(scenario, viewer);
    const allocs = scenario.allocations || [];
    const winsById = new Map();
    for (const w of (scenario.access_windows || [])) winsById.set(w.window_id, w);

    // Bucket allocations by current stage
    const buckets = {
      BIDDED: [], COLLECTING: [], PROCESSING: [],
      IN_TRANSIT: [], DELIVERED: [],
      DEADLINE_MISSED: [], PROCESSING_FAILED: [], DROPPED: [],
    };
    for (const a of allocs) {
      const w = a.window_id ? winsById.get(a.window_id) : null;
      const stage = _stageAt(a, w, t_ms);
      if (buckets[stage]) buckets[stage].push({ a, w });
      else if (stage === "PENDING") buckets.BIDDED.push({ a, w });
    }
    // Sort each bucket by priority desc
    for (const k in buckets) {
      buckets[k].sort((x, y) => (y.a.priority_score || 0) - (x.a.priority_score || 0));
    }

    function makeColumn(stage, isFailure) {
      const col = document.createElement("div");
      col.className = "kb-col" + (isFailure ? " kb-col-fail" : "");
      const head = document.createElement("div");
      head.className = "kb-col-head";
      head.style.borderTopColor = STAGE_COLOR[stage] || "#5a6675";
      const lbl = document.createElement("span");
      lbl.className = "kb-col-label";
      lbl.textContent = STAGE_LABEL[stage] || stage;
      const cnt = document.createElement("span");
      cnt.className = "kb-col-count";
      cnt.textContent = buckets[stage].length;
      head.appendChild(lbl); head.appendChild(cnt);
      col.appendChild(head);

      const body = document.createElement("div");
      body.className = "kb-col-body";
      const max_cards = 60;
      const items = buckets[stage].slice(0, max_cards);
      for (const { a, w } of items) {
        body.appendChild(_buildKanbanCard(a, w, w ? w.target_id : null, null));
      }
      if (buckets[stage].length > max_cards) {
        const more = document.createElement("div");
        more.className = "kb-more";
        more.textContent = "… and " + (buckets[stage].length - max_cards) + " more";
        body.appendChild(more);
      }
      if (buckets[stage].length === 0) {
        const empty = document.createElement("div");
        empty.className = "kb-empty";
        empty.textContent = "—";
        body.appendChild(empty);
      }
      col.appendChild(body);
      return col;
    }

    const flow = document.createElement("div");
    flow.className = "kb-flow";
    KANBAN_COLUMNS.forEach((stage) => flow.appendChild(makeColumn(stage, false)));
    root.appendChild(flow);

    // Failures pane
    const failTotal = FAILURE_COLUMNS.reduce((s, k) => s + buckets[k].length, 0);
    if (failTotal > 0) {
      const failHead = document.createElement("div");
      failHead.className = "kb-fail-head";
      failHead.textContent = "TERMINAL FAILURES — " + failTotal;
      root.appendChild(failHead);
      const failFlow = document.createElement("div");
      failFlow.className = "kb-flow kb-flow-fail";
      FAILURE_COLUMNS.forEach((stage) => failFlow.appendChild(makeColumn(stage, true)));
      root.appendChild(failFlow);
    }
  }

  // ---------- Public API ----------

  function init(scenario, viewer) {
    const overlay = document.getElementById("board-overlay");
    if (!overlay) return null;

    let lastTickRender = 0;
    let visible = false;

    function show() {
      visible = true;
      overlay.classList.add("active");
      renderGantt(scenario);
      renderKanban(scenario, viewer);
      updateGanttPlayhead(scenario, viewer);
    }
    function hide() {
      visible = false;
      overlay.classList.remove("active");
    }
    function isVisible() { return visible; }

    // Re-render kanban every ~half second of real time when visible;
    // playhead updates more frequently.
    viewer.clock.onTick.addEventListener(() => {
      if (!visible) return;
      const now = performance.now();
      updateGanttPlayhead(scenario, viewer);
      if (now - lastTickRender > 500) {
        renderKanban(scenario, viewer);
        lastTickRender = now;
      }
    });

    return { show, hide, isVisible };
  }

  global.RavenEyeBoard = { init };
})(window);
